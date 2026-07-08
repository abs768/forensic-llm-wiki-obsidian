"""Ingest operation.

Walks ``raw_sources/<case>/``, calls the LLM client on each file, merges the
returned facts into the case's :class:`WikiState`, and re-renders all
markdown pages. The raw sources themselves are never touched.

The merge happens in two passes:

1. **Extraction pass** — per file, pull entities/events/IOCs/hypotheses and
   add them to a temporary accumulator. This is order-independent because no
   contradiction detection runs yet.
2. **Contradiction pass** — with the full accumulator in hand, re-visit each
   file so contradiction extractors can compare new evidence against the
   *whole* current picture (e.g. the Defender clean-scan only becomes a
   contradiction once persistence is in the wiki).

Phase 2 additions:
- Source manifest at ``.fw/manifest.json`` (skip unchanged files by default).
- Structured indexes (events / entities / claims JSON).
- Trace log per file and per run.
- Dry-run mode that computes the new state, renders pages in memory, and
  prints a unified diff against the current on-disk pages — without writing.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .index import assign_ids, write_indexes
from .llm import LLMClient
from .manifest import (
    load_manifest,
    mark_ingest_run,
    needs_processing,
    record_processed,
    save_manifest,
)
from .review import create_review, scan_for_risky_phrases
from .schemas import (
    IOC,
    Contradiction,
    Entity,
    Event,
    ExtractedFacts,
    Hypothesis,
    IngestionLogEntry,
)
from .tracing import Tracer, append_ingestion_log
from .wiki_io import (
    WikiState,
    case_dir,
    ensure_case_structure,
    file_hash,
    load_state,
    raw_case_dir,
    read_existing_pages,
    render_all_pages,
    render_pages,
    save_state,
)


@dataclass
class IngestReport:
    case_id: str
    sources_processed: list[str] = field(default_factory=list)
    sources_skipped: list[str] = field(default_factory=list)
    pages_written: list[str] = field(default_factory=list)
    pages_changed: list[str] = field(default_factory=list)
    page_diffs: dict[str, str] = field(default_factory=dict)
    dry_run: bool = False
    review_mode: bool = False
    pages_queued_for_review: list[str] = field(default_factory=list)
    review_ids: list[str] = field(default_factory=list)
    mode: str = "mock"


CONFIDENCE_RANK = {"Low": 1, "Medium": 2, "High": 3, "Confirmed": 4}


def ingest_case(
    project_root: Path,
    case_id: str,
    *,
    llm: LLMClient | None = None,
    force: bool = False,
    changed_only: bool = False,
    dry_run: bool = False,
    trace: bool = True,
    subdir: str | None = None,
    review: bool = False,
) -> IngestReport:
    """Run an ingest. By default processes new/changed files only.

    ``force``        — reprocess every file regardless of manifest.
    ``changed_only`` — same as the default but explicitly asked for.
    ``dry_run``      — compute and diff but do not write anything.
    ``subdir``       — restrict file enumeration to ``raw_sources/<case>/<subdir>``.
                       Used by ``fw.py evolve`` to ingest one step at a time.
    """
    raw_dir = raw_case_dir(project_root, case_id)
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw case directory not found: {raw_dir}")
    walk_root = raw_dir / subdir if subdir else raw_dir
    if subdir and not walk_root.exists():
        raise FileNotFoundError(f"Subdirectory not found: {walk_root}")

    llm = llm or LLMClient()
    state = load_state(project_root, case_id)
    state.case_id = case_id
    if not dry_run:
        ensure_case_structure(project_root, case_id)
    manifest = load_manifest(project_root, case_id)
    manifest.case_id = case_id

    files = sorted(_enumerate_files(walk_root))
    report = IngestReport(case_id=case_id, dry_run=dry_run, mode=llm.mode)

    # Pass 1: per-file extraction, wrapped in traces.
    new_extractions: list[tuple[str, ExtractedFacts]] = []  # (rel_path, facts)
    for path in files:
        rel = _relative(project_root, path)
        with Tracer(project_root, case_id, "ingest", source_path=rel, enabled=trace and not dry_run) as tr:
            with tr.step("hash_source"):
                h = file_hash(path)
            should_process = force or needs_processing(manifest, rel, h)
            if changed_only and not should_process:
                should_process = False
            if not should_process:
                with tr.step("skip") as ctx:
                    ctx.mark_skipped("unchanged")
                report.sources_skipped.append(rel)
                continue
            with tr.step("extract_facts"):
                facts = llm.extract(
                    path,
                    prior_hypotheses=list(state.hypotheses.values()),
                    prior_iocs=list(state.iocs.values()),
                )
                facts.source_path = rel
                _rebase_paths(facts, project_root)
            new_extractions.append((rel, facts))
            state.source_files[rel] = h
            report.sources_processed.append(rel)

    # Pass 1b: merge entities/events/IOCs/hypotheses.
    for _, facts in new_extractions:
        _merge_facts(state, facts, include_contradictions=False)

    # Pass 2: order-independent contradiction detection.
    if new_extractions:
        from . import claim_extractor
        from .parsers import parse

        for path in files:
            source = parse(path)
            new_conflicts = claim_extractor.extract_contradictions(
                source,
                prior_hypotheses=list(state.hypotheses.values()),
                prior_iocs=list(state.iocs.values()),
            )
            for c in new_conflicts:
                c.claim_a = _fix_in_evidence_string(c.claim_a, project_root)
                c.claim_b = _fix_in_evidence_string(c.claim_b, project_root)
                _add_contradiction(state, c)

    state.last_updated = _now()
    assign_ids(state)

    # Render proposed pages in memory.
    proposed = render_pages(state)
    existing = read_existing_pages(project_root, case_id)
    for name, new_body in proposed.items():
        old = existing.get(name, "")
        if old != new_body:
            report.pages_changed.append(name)
            report.page_diffs[name] = _unified_diff(old, new_body, name)

    if dry_run:
        # Compute the would-touch list per source so the report reflects
        # what would be written, then bail without touching the filesystem.
        for rel, _ in new_extractions:
            record_processed(manifest, rel, state.source_files[rel],
                             report.pages_changed, status="processed")
        report.pages_written = []
        return report

    # Commit: state, manifest, markdown, indexes, ingestion log.
    save_state(project_root, state)
    pages = render_all_pages(project_root, state)
    report.pages_written = list(pages.keys())
    write_indexes(project_root, state)

    # Phase 6: in --review mode, any page whose freshly-rendered content
    # contains a risky phrase (e.g. "confirmed malware") that the prior
    # content lacked gets reverted on disk and queued as a review item.
    # Safe pages still update; the state/indexes always reflect what
    # extraction found.
    if review:
        report.review_mode = True
        cdir = case_dir(project_root, case_id)
        for name, new_body in pages.items():
            risky_new = scan_for_risky_phrases(new_body)
            risky_old = scan_for_risky_phrases(existing.get(name, ""))
            newly_risky = [p for p in risky_new if p not in risky_old]
            if not newly_risky:
                continue
            prior = existing.get(name, "")
            (cdir / name).write_text(prior)
            item = create_review(
                project_root, case_id,
                change_type="wiki_update",
                target_page=name,
                proposed_content=new_body,
                prior_content=prior,
                reason=(
                    f"Risky phrase(s) {newly_risky!r} appeared in proposed "
                    f"{name}; held for human review."
                ),
                risky_phrases=newly_risky,
            )
            report.pages_queued_for_review.append(name)
            report.review_ids.append(item.review_id)

    for rel, _ in new_extractions:
        record_processed(manifest, rel, state.source_files[rel],
                         report.pages_changed, status="processed")
    mark_ingest_run(manifest)
    save_manifest(project_root, manifest)

    append_ingestion_log(project_root, IngestionLogEntry(
        case_id=case_id,
        sources_processed=report.sources_processed,
        sources_skipped=report.sources_skipped,
        pages_written=report.pages_written,
        mode=report.mode,
        dry_run=False,
    ))
    return report


# --------------------------------------------------------------------------- #
# Diff helper
# --------------------------------------------------------------------------- #


def _enumerate_files(root: Path) -> list[Path]:
    """Recursively walk a directory, skipping dotfiles and dot-dirs."""
    out: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        if path.name.startswith("."):
            continue
        out.append(path)
    return out


def _unified_diff(old: str, new: str, name: str) -> str:
    old_lines = old.splitlines(keepends=True) if old else []
    new_lines = new.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{name}",
        tofile=f"b/{name}",
        n=2,
    )
    return "".join(diff)


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def format_dry_run(report: IngestReport) -> str:
    """Human-readable summary of a dry-run ingest."""
    lines: list[str] = []
    lines.append(f"Dry-run ingest of case '{report.case_id}' (mode={report.mode}).")
    lines.append(f"  Sources that would be processed: {len(report.sources_processed)}")
    for s in report.sources_processed:
        lines.append(f"    + {s}")
    if report.sources_skipped:
        lines.append(f"  Sources unchanged (would skip): {len(report.sources_skipped)}")
        for s in report.sources_skipped:
            lines.append(f"    = {s}")
    if not report.pages_changed:
        lines.append("  No wiki pages would change.")
        return "\n".join(lines)
    lines.append(f"  Wiki pages that would change: {len(report.pages_changed)}")
    for name in report.pages_changed:
        lines.append(f"    ~ {name}")
    lines.append("")
    for name, diff in report.page_diffs.items():
        lines.append(f"--- Would update: wiki/cases/{report.case_id}/{name} ---")
        if diff:
            lines.append(diff.rstrip())
        else:
            lines.append("(new file)")
        lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Merge helpers
# --------------------------------------------------------------------------- #


def _merge_facts(
    state: WikiState,
    facts: ExtractedFacts,
    *,
    include_contradictions: bool,
) -> None:
    for entity in facts.entities:
        _add_entity(state, entity)
    for event in facts.events:
        _add_event(state, event)
    for ioc in facts.iocs:
        _add_ioc(state, ioc)
    for hyp in facts.hypotheses:
        _add_hypothesis(state, hyp)
    if include_contradictions:
        for c in facts.contradictions:
            _add_contradiction(state, c)
    for q in facts.open_questions:
        _add_open_question(state, q)


def _add_entity(state: WikiState, new: Entity) -> None:
    existing = state.entities.get(new.key)
    if existing is None:
        state.entities[new.key] = new
        return
    existing.appears_in = sorted(set(existing.appears_in) | set(new.appears_in))
    existing.related = sorted(set(existing.related) | set(new.related))
    seen = {(c.kind, c.target) for c in existing.citations}
    for c in new.citations:
        if (c.kind, c.target) not in seen:
            existing.citations.append(c)
            seen.add((c.kind, c.target))


def _add_event(state: WikiState, new: Event) -> None:
    key = (new.timestamp, new.description, new.citation.target)
    for ev in state.events:
        if (ev.timestamp, ev.description, ev.citation.target) == key:
            return
    state.events.append(new)


def _add_ioc(state: WikiState, new: IOC) -> None:
    key = f"{new.type}:{new.artifact.lower()}"
    existing = state.iocs.get(key)
    if existing is None:
        state.iocs[key] = new
        return
    if CONFIDENCE_RANK[new.confidence] > CONFIDENCE_RANK[existing.confidence]:
        existing.confidence = new.confidence
    existing.related = sorted(set(existing.related) | set(new.related))
    if existing.first_seen == "unknown":
        existing.first_seen = new.first_seen


def _add_hypothesis(state: WikiState, new: Hypothesis) -> None:
    key = new.title.lower()
    existing = state.hypotheses.get(key)
    if existing is None:
        state.hypotheses[key] = new
        return
    existing.facts = _merge_str_list(existing.facts, new.facts)
    existing.supporting_evidence = _merge_str_list(
        existing.supporting_evidence, new.supporting_evidence
    )
    existing.contradicting_evidence = _merge_str_list(
        existing.contradicting_evidence, new.contradicting_evidence
    )
    existing.open_questions = _merge_str_list(existing.open_questions, new.open_questions)
    existing.next_steps = _merge_str_list(existing.next_steps, new.next_steps)
    if new.inference and not existing.inference:
        existing.inference = new.inference
    if CONFIDENCE_RANK[new.confidence] > CONFIDENCE_RANK[existing.confidence]:
        existing.confidence = new.confidence


def _add_contradiction(state: WikiState, new: Contradiction) -> None:
    key = new.title.lower()
    if key not in state.contradictions:
        state.contradictions[key] = new


def _add_open_question(state: WikiState, q: str) -> None:
    if q not in state.open_questions:
        state.open_questions.append(q)


def _merge_str_list(a: list[str], b: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in a + b:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _relative(project_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def _rebase_paths(facts: ExtractedFacts, project_root: Path) -> None:
    """Rewrite any absolute paths in extracted citations to project-relative."""
    rel = facts.source_path

    def fix(s: str) -> str:
        if not s:
            return s
        try:
            return str(Path(s).relative_to(project_root))
        except ValueError:
            return s

    for e in facts.entities:
        e.appears_in = [fix(a) for a in e.appears_in]
        for c in e.citations:
            c.target = fix(c.target)
    for ev in facts.events:
        ev.citation.target = fix(ev.citation.target)
    for i in facts.iocs:
        i.source = fix(i.source)
    for h in facts.hypotheses:
        h.supporting_evidence = [
            _fix_in_evidence_string(s, project_root) for s in h.supporting_evidence
        ]
        h.contradicting_evidence = [
            _fix_in_evidence_string(s, project_root) for s in h.contradicting_evidence
        ]
    for contra in facts.contradictions:
        contra.claim_a = _fix_in_evidence_string(contra.claim_a, project_root)
        contra.claim_b = _fix_in_evidence_string(contra.claim_b, project_root)
    # Open questions are plain strings, nothing to rebase.
    _ = rel


def _fix_in_evidence_string(s: str, project_root: Path) -> str:
    """Rewrite an embedded absolute path inside a free-text evidence string."""
    root = str(project_root)
    if root in s:
        return s.replace(root + "/", "").replace(root, "")
    return s
