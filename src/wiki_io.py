"""I/O for the wiki layer.

The wiki on disk is markdown for humans, plus a small ``_state.json`` per
case that holds the structured snapshot of everything the maintainer
believes. Markdown is rendered from state on every ingest, so the two
representations cannot diverge.

This module is intentionally I/O-only: it loads and saves state and renders
markdown. The merge logic that turns raw extractions into state lives in
``ingest.py``.
"""
from __future__ import annotations

import hashlib
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from .schemas import IOC, Contradiction, Entity, Event, Hypothesis

# --------------------------------------------------------------------------- #
# Fingerprints for stable IDs
# --------------------------------------------------------------------------- #


def event_fingerprint(ev: Event) -> str:
    return f"{ev.timestamp}|{ev.description}|{ev.citation.target}"


def hypothesis_key(h: Hypothesis) -> str:
    return h.title.lower()


# Pages required by the schema. Used by lint and by ensure_case_structure.
REQUIRED_PAGES: tuple[str, ...] = (
    "index.md",
    "timeline.md",
    "entities.md",
    "iocs.md",
    "hypotheses.md",
    "contradictions.md",
    "open_questions.md",
    "final_report.md",
)


class WikiState(BaseModel):
    """Compiled, structured snapshot of one case wiki."""

    case_id: str
    entities: dict[str, Entity] = Field(default_factory=dict)
    events: list[Event] = Field(default_factory=list)
    iocs: dict[str, IOC] = Field(default_factory=dict)
    hypotheses: dict[str, Hypothesis] = Field(default_factory=dict)
    contradictions: dict[str, Contradiction] = Field(default_factory=dict)
    open_questions: list[str] = Field(default_factory=list)
    source_files: dict[str, str] = Field(default_factory=dict)  # path -> sha256
    last_updated: str = ""

    # Phase 2: stable IDs (assigned once, persisted across re-ingests).
    # Keyed by a canonical fingerprint of the underlying record.
    event_ids: dict[str, str] = Field(default_factory=dict)       # fp -> "evt_NNNN"
    entity_ids: dict[str, str] = Field(default_factory=dict)      # key -> "ent_NNNN"
    claim_ids: dict[str, str] = Field(default_factory=dict)       # key -> "claim_NNNN"
    id_counters: dict[str, int] = Field(default_factory=dict)     # kind -> next-int

    def source_count(self) -> int:
        return len(self.source_files)

    def next_id(self, kind: str, width: int = 4) -> str:
        prefix = {"event": "evt", "entity": "ent", "claim": "claim"}[kind]
        n = self.id_counters.get(kind, 0) + 1
        self.id_counters[kind] = n
        return f"{prefix}_{n:0{width}d}"


# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #


def wiki_root(project_root: Path) -> Path:
    return project_root / "wiki"


def case_dir(project_root: Path, case_id: str) -> Path:
    return wiki_root(project_root) / "cases" / case_id


def fw_dir(project_root: Path, case_id: str) -> Path:
    """Internal Phase 2 sidecar directory: manifest, state, indexes, traces."""
    return case_dir(project_root, case_id) / ".fw"


def state_path(project_root: Path, case_id: str) -> Path:
    return fw_dir(project_root, case_id) / "state.json"


def legacy_state_path(project_root: Path, case_id: str) -> Path:
    """Phase 1 state location, kept for transparent migration."""
    return case_dir(project_root, case_id) / "_state.json"


def raw_case_dir(project_root: Path, case_id: str) -> Path:
    return project_root / "raw_sources" / case_id


# --------------------------------------------------------------------------- #
# Hashing
# --------------------------------------------------------------------------- #


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# State load / save
# --------------------------------------------------------------------------- #


def ensure_case_structure(project_root: Path, case_id: str) -> Path:
    cdir = case_dir(project_root, case_id)
    cdir.mkdir(parents=True, exist_ok=True)
    fw_dir(project_root, case_id).mkdir(parents=True, exist_ok=True)
    wiki_index = wiki_root(project_root) / "index.md"
    if not wiki_index.exists():
        wiki_index.write_text(_render_root_index([case_id]))
    return cdir


def load_state(project_root: Path, case_id: str) -> WikiState:
    sp = state_path(project_root, case_id)
    if sp.exists():
        return WikiState.model_validate_json(sp.read_text())
    # Phase 1 compatibility: migrate the old location if present.
    legacy = legacy_state_path(project_root, case_id)
    if legacy.exists():
        state = WikiState.model_validate_json(legacy.read_text())
        save_state(project_root, state)
        return state
    return WikiState(case_id=case_id)


def save_state(project_root: Path, state: WikiState) -> None:
    sp = state_path(project_root, state.case_id)
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(state.model_dump_json(indent=2))


# --------------------------------------------------------------------------- #
# Markdown rendering
# --------------------------------------------------------------------------- #


def render_all_pages(project_root: Path, state: WikiState) -> dict[str, str]:
    """Render every page from state and write to disk. Returns {filename: content}."""
    cdir = ensure_case_structure(project_root, state.case_id)
    pages = render_pages(state)

    # Preserve any existing final_report.md unless the report operation
    # rewrote it — the lint required-page check needs at least a stub.
    fr = cdir / "final_report.md"
    if fr.exists():
        pages["final_report.md"] = fr.read_text()
    else:
        pages["final_report.md"] = _render_report_stub(state)

    write_pages(project_root, state.case_id, pages)
    return pages


def render_pages(state: WikiState) -> dict[str, str]:
    """Pure render — produces page contents but does not touch the filesystem.

    Used by ``--dry-run`` and by ``render_all_pages``. Does not include
    final_report.md (that page is owned by the report operation, which
    composes from the same state).
    """
    return {
        "index.md": _render_index(state),
        "timeline.md": _render_timeline(state),
        "entities.md": _render_entities(state),
        "iocs.md": _render_iocs(state),
        "hypotheses.md": _render_hypotheses(state),
        "contradictions.md": _render_contradictions(state),
        "open_questions.md": _render_open_questions(state),
    }


def write_pages(project_root: Path, case_id: str, pages: dict[str, str]) -> None:
    cdir = ensure_case_structure(project_root, case_id)
    for name, body in pages.items():
        (cdir / name).write_text(body)
    # Refresh the root wiki index so new cases appear there.
    cases_dir = wiki_root(project_root) / "cases"
    if cases_dir.exists():
        root_cases = sorted(p.name for p in cases_dir.iterdir() if p.is_dir())
        (wiki_root(project_root) / "index.md").write_text(_render_root_index(root_cases))


def read_existing_pages(project_root: Path, case_id: str) -> dict[str, str]:
    """Read whatever markdown pages currently exist on disk. Empty dict if none."""
    cdir = case_dir(project_root, case_id)
    if not cdir.exists():
        return {}
    out: dict[str, str] = {}
    for name in REQUIRED_PAGES:
        p = cdir / name
        if p.exists():
            out[name] = p.read_text()
    return out


def _front_matter(case_id: str, page: str, state: WikiState) -> str:
    updated = state.last_updated or datetime.utcnow().isoformat(timespec="seconds") + "Z"
    return (
        "---\n"
        f"case: {case_id}\n"
        f"page: {page}\n"
        f"updated: {updated}\n"
        f"sources: {state.source_count()}\n"
        "---\n\n"
    )


def _render_root_index(case_ids: Iterable[str]) -> str:
    lines = ["# Forensic LLM Wiki", "", "## Cases", ""]
    for cid in sorted(set(case_ids)):
        lines.append(f"- [[cases/{cid}/index|{cid}]]")
    lines.append("")
    return "\n".join(lines)


def _render_index(state: WikiState) -> str:
    out = [_front_matter(state.case_id, "index", state)]
    out.append(f"# Case {state.case_id}\n")

    assessment, confidence = _summarise_assessment(state)
    out.append("## Current Assessment\n")
    out.append(f"{assessment} (overall confidence: **{confidence}**)\n")

    out.append("## Key Evidence\n")
    if state.iocs:
        for ioc in sorted(state.iocs.values(), key=lambda i: i.artifact):
            out.append(
                f"- **{ioc.artifact}** ({ioc.type}) — {ioc.reason} "
                f"(Source: {ioc.source})"
            )
    else:
        out.append("- _no IOCs recorded yet_")
    out.append("")

    out.append("## Key Open Questions\n")
    if state.open_questions:
        for q in state.open_questions[:5]:
            out.append(f"- {q}")
        if len(state.open_questions) > 5:
            out.append(f"- ... and {len(state.open_questions) - 5} more in [[open_questions]]")
    else:
        out.append("- _none recorded yet_")
    out.append("")

    out.append("## Pages\n")
    out.append("- [[timeline]]")
    out.append("- [[entities]]")
    out.append("- [[iocs]]")
    out.append("- [[hypotheses]]")
    out.append("- [[contradictions]]")
    out.append("- [[open_questions]]")
    out.append("- [[final_report]]")
    out.append("")
    return "\n".join(out)


def _summarise_assessment(state: WikiState) -> tuple[str, str]:
    """Produce a conservative one-line summary of the case state."""
    if not state.hypotheses:
        return ("No hypotheses have been formed yet.", "Low")
    confs = [h.confidence for h in state.hypotheses.values()]
    rank = {"Low": 1, "Medium": 2, "High": 3, "Confirmed": 4}
    top = max(confs, key=lambda c: rank.get(c, 0))
    titles = [h.title for h in state.hypotheses.values() if h.confidence == top]
    title_phrase = "; ".join(titles[:3])
    contradiction_note = ""
    if state.contradictions:
        contradiction_note = (
            f" {len(state.contradictions)} active contradiction(s) prevent firmer claims."
        )
    return (
        f"Strongest open hypothesis: {title_phrase}.{contradiction_note}",
        top,
    )


def _render_timeline(state: WikiState) -> str:
    out = [_front_matter(state.case_id, "timeline", state)]
    out.append("# Timeline\n")
    out.append("| ID | Timestamp | Event | Source |")
    out.append("|---|---|---|---|")

    def sort_key(e: Event) -> tuple[int, str]:
        ts = e.timestamp or "unknown"
        return (0 if ts != "unknown" else 1, ts)

    if not state.events:
        out.append("| | _no events yet_ | | |")
    for ev in sorted(state.events, key=sort_key):
        eid = state.event_ids.get(event_fingerprint(ev), "evt_????")
        desc = ev.description.replace("|", "\\|")
        out.append(
            f"| {eid} | {ev.timestamp or 'unknown'} | {desc} | "
            f"Source: {ev.citation.target} |"
        )
    out.append("")
    return "\n".join(out)


def _render_entities(state: WikiState) -> str:
    out = [_front_matter(state.case_id, "entities", state)]
    out.append("# Entities\n")
    if not state.entities:
        out.append("_no entities recorded yet_")
        return "\n".join(out) + "\n"
    for key in sorted(state.entities):
        e = state.entities[key]
        ent_id = state.entity_ids.get(key, "ent_????")
        out.append(f"## {e.heading}  ({ent_id})\n")
        out.append(f"- Type: {e.type}")
        out.append(f"- Value: {e.value}")
        if e.appears_in:
            out.append("- Appears in: " + ", ".join(sorted(set(e.appears_in))))
        if e.related:
            out.append("- Related: " + ", ".join(sorted(set(e.related))))
        if e.citations:
            out.append("- Citations:")
            for c in e.citations:
                out.append(f"  - {c.render()}")
        out.append("")
    return "\n".join(out)


def _render_iocs(state: WikiState) -> str:
    out = [_front_matter(state.case_id, "iocs", state)]
    out.append("# Indicators of Compromise\n")
    out.append("| Artifact | Type | First Seen | Source | Confidence | Reason | Related |")
    out.append("|---|---|---|---|---|---|---|")
    if not state.iocs:
        out.append("| _no IOCs yet_ | | | | | | |")
    for key in sorted(state.iocs):
        i = state.iocs[key]
        related = ", ".join(i.related) if i.related else ""
        reason = i.reason.replace("|", "\\|")
        out.append(
            f"| {i.artifact} | {i.type} | {i.first_seen} | {i.source} | "
            f"{i.confidence} | {reason} | {related} |"
        )
    out.append("")
    return "\n".join(out)


def _render_hypotheses(state: WikiState) -> str:
    out = [_front_matter(state.case_id, "hypotheses", state)]
    out.append("# Hypotheses\n")
    if not state.hypotheses:
        out.append("_no hypotheses recorded yet_")
        return "\n".join(out) + "\n"
    for key in sorted(state.hypotheses):
        h = state.hypotheses[key]
        claim_id = state.claim_ids.get(hypothesis_key(h), "claim_????")
        out.append(f"## {h.title}  ({claim_id})\n")
        out.append(f"Confidence: {h.confidence}\n")
        out.append("### Facts")
        for f in h.facts or ["_none recorded_"]:
            out.append(f"- {f}")
        out.append("")
        out.append("### Inference")
        out.append(h.inference or "_none recorded_")
        out.append("")
        out.append("### Supporting Evidence")
        for s in h.supporting_evidence or ["_none recorded_"]:
            out.append(f"- {s}")
        out.append("")
        out.append("### Contradicting Evidence")
        if h.contradicting_evidence:
            for c in h.contradicting_evidence:
                out.append(f"- {c}")
        else:
            out.append("- None recorded — see [[contradictions]] for active conflicts.")
        out.append("")
        out.append("### Open Questions")
        for q in h.open_questions or ["_none recorded_"]:
            out.append(f"- {q}")
        out.append("")
        out.append("### Next Steps")
        for n in h.next_steps or ["_none recorded_"]:
            out.append(f"- {n}")
        out.append("")
    return "\n".join(out)


def _render_contradictions(state: WikiState) -> str:
    out = [_front_matter(state.case_id, "contradictions", state)]
    out.append("# Contradictions\n")
    if not state.contradictions:
        out.append("_no contradictions recorded_")
        return "\n".join(out) + "\n"
    for key in sorted(state.contradictions):
        c = state.contradictions[key]
        out.append(f"## {c.title}\n")
        out.append(f"- Claim A: {c.claim_a}")
        out.append(f"- Claim B: {c.claim_b}")
        out.append(f"- Status: {c.status}")
        out.append("")
    return "\n".join(out)


def _render_open_questions(state: WikiState) -> str:
    out = [_front_matter(state.case_id, "open_questions", state)]
    out.append("# Open Questions\n")
    if not state.open_questions:
        out.append("- _none recorded_")
    for q in state.open_questions:
        out.append(f"- [ ] {q}")
    out.append("")
    return "\n".join(out)


def _render_report_stub(state: WikiState) -> str:
    out = [_front_matter(state.case_id, "final_report", state)]
    out.append(f"# Final Report — Case {state.case_id}\n")
    out.append("> Draft stub. Run `fw.py report <case>` to generate the full report.\n")
    out.append("## Executive Summary")
    out.append("_pending_\n")
    return "\n".join(out)
