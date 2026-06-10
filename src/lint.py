"""Lint operation.

Reads the case wiki and applies the rules from ``schema/lint_rules.md``.
Lint never modifies files; it only reports.

Phase 2 changes:
- Severity escalated to four tiers: critical / high / medium / low.
- New rules covering manifest-vs-wiki drift and weak high-confidence claims.
- ``--json`` output via :func:`format_json`.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path

from .manifest import load_manifest
from .schemas import LintFinding, LintReport
from .wiki_io import REQUIRED_PAGES, case_dir, load_state, raw_case_dir

_CONFIRMATION_PHRASES = (
    "confirmed malware",
    "malware confirmed",
    "confirmed exfiltration",
    "confirmed compromise",
    "definite malware",
    "definitely malicious",
)

_WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
_RAW_CITATION_RE = re.compile(r"raw_sources/[^\s,)]+")


def lint_case(project_root: Path, case_id: str) -> LintReport:
    findings: list[LintFinding] = []
    cdir = case_dir(project_root, case_id)
    state = load_state(project_root, case_id)
    manifest = load_manifest(project_root, case_id)

    page_contents: dict[str, str] = {}
    for name in REQUIRED_PAGES:
        p = cdir / name
        if not p.exists():
            findings.append(LintFinding(
                rule="H1",
                severity="High",
                page=name,
                message=f"Required page '{name}' is missing for case {case_id}.",
            ))
            continue
        page_contents[name] = p.read_text()

    _check_unsupported_confirmation(findings, state, page_contents)
    _check_final_report_overclaim(findings, state, page_contents)
    _check_broken_raw_citations(findings, project_root, page_contents)
    _check_hypotheses_structure(findings, state)
    _check_high_confidence_weak_evidence(findings, state)
    _check_missing_citations(findings, state)
    _check_broken_wiki_links(findings, page_contents)
    _check_duplicate_entities(findings, state)
    _check_orphan_pages(findings, page_contents)
    _check_exfiltration_overclaim(findings, state, page_contents)
    _check_final_report_claims_match_index(findings, project_root, case_id, page_contents)
    _check_suggest_review_mode(findings)
    _check_orphan_entities(findings, state, page_contents)
    _check_ioc_cross_refs(findings, state)
    _check_contradictions_state_vs_page(findings, state, page_contents)
    _check_raw_sources_never_ingested(findings, project_root, case_id, manifest)
    _check_stale_pages(findings, project_root, case_id, manifest)

    return LintReport(findings=findings, case_id=case_id)


# --------------------------------------------------------------------------- #
# Critical / High rules
# --------------------------------------------------------------------------- #


_ATTRIBUTION_MARKERS = (
    "investigator", "analyst", "asserts", "alleges", "claims", "claim a:",
    "claim b:", "describes", "describe", "diagnosis", "note:", "notes:",
    "quoted", "according to", "says", "argues", "reported",
)


def _line_is_attributed(line: str) -> bool:
    """True if the line clearly *reports* someone else's claim rather than
    asserting it. We use this to suppress C1 on lines like
    'Investigator note: Dana asserts: malware confirmed', which is the wiki
    faithfully recording an overclaim, not making one."""
    line_lower = line.lower()
    return any(marker in line_lower for marker in _ATTRIBUTION_MARKERS)


def _check_unsupported_confirmation(findings, state, pages) -> None:
    """C1 — wiki uses 'confirmed malware' without a strong hypothesis backing it."""
    strong_hyps = [
        h for h in state.hypotheses.values()
        if h.confidence in ("High", "Confirmed")
        and len(h.supporting_evidence) >= 2
    ]
    if strong_hyps:
        return
    for name, text in pages.items():
        for raw_line in text.splitlines():
            line_lower = raw_line.lower()
            for phrase in _CONFIRMATION_PHRASES:
                if phrase not in line_lower:
                    continue
                if _line_is_attributed(raw_line):
                    continue
                findings.append(LintFinding(
                    rule="C1",
                    severity="Critical",
                    page=name,
                    message=(
                        f"Page '{name}' uses the phrase '{phrase}', but no "
                        f"High/Confirmed hypothesis with >= 2 supporting "
                        f"evidence bullets backs that claim."
                    ),
                ))
                break  # one finding per line is enough


def _check_final_report_overclaim(findings, state, pages) -> None:
    """C2 — final report says more than the strongest hypothesis supports."""
    fr = pages.get("final_report.md", "")
    if not fr:
        return
    max_rank = max(
        ({"Low": 1, "Medium": 2, "High": 3, "Confirmed": 4}.get(h.confidence, 0)
         for h in state.hypotheses.values()),
        default=0,
    )
    if max_rank < 3:
        for phrase in _CONFIRMATION_PHRASES:
            if phrase in fr.lower():
                findings.append(LintFinding(
                    rule="C2",
                    severity="Critical",
                    page="final_report.md",
                    message=(
                        f"final_report.md contains '{phrase}', but the "
                        f"strongest hypothesis is below High confidence."
                    ),
                ))


def _check_broken_raw_citations(findings, project_root, pages) -> None:
    """C3 — citation points at a raw_sources file that does not exist."""
    for name, text in pages.items():
        for match in _RAW_CITATION_RE.findall(text):
            cleaned = match.rstrip(").,;'\"")
            ref = (project_root / cleaned).resolve()
            if not ref.exists():
                findings.append(LintFinding(
                    rule="C3",
                    severity="Critical",
                    page=name,
                    message=f"Citation '{cleaned}' does not resolve to an existing file.",
                ))


def _check_high_confidence_weak_evidence(findings, state) -> None:
    """H3 — claim marked High/Confirmed but lacks two supporting bullets."""
    for h in state.hypotheses.values():
        if h.confidence in ("High", "Confirmed") and len(h.supporting_evidence) < 2:
            findings.append(LintFinding(
                rule="H3",
                severity="High",
                page="hypotheses.md",
                message=(
                    f"Hypothesis '{h.title}' is marked {h.confidence} but "
                    f"only has {len(h.supporting_evidence)} supporting "
                    f"evidence bullet(s); High requires >= 2."
                ),
            ))


def _check_raw_sources_never_ingested(findings, project_root, case_id, manifest) -> None:
    """H2 — files present in raw_sources/<case>/ but not in the manifest."""
    raw_dir = raw_case_dir(project_root, case_id)
    if not raw_dir.exists():
        return
    known = manifest.by_path()
    for path in sorted(raw_dir.rglob("*")):
        if not path.is_file():
            continue
        if any(part.startswith(".") for part in path.relative_to(raw_dir).parts):
            continue
        rel = str(path.relative_to(project_root))
        if rel not in known:
            findings.append(LintFinding(
                rule="H2",
                severity="High",
                page=rel,
                message=f"Raw source '{rel}' has never been ingested into the wiki.",
            ))


# --------------------------------------------------------------------------- #
# Medium rules
# --------------------------------------------------------------------------- #


def _check_hypotheses_structure(findings, state) -> None:
    for h in state.hypotheses.values():
        if not h.facts and h.inference:
            findings.append(LintFinding(
                rule="M2",
                severity="Medium",
                page="hypotheses.md",
                message=(
                    f"Hypothesis '{h.title}' has an inference but lists no facts."
                ),
            ))
        if not h.contradicting_evidence and not _has_related_contradiction(state, h):
            findings.append(LintFinding(
                rule="M1",
                severity="Medium",
                page="hypotheses.md",
                message=(
                    f"Hypothesis '{h.title}' lists no contradicting evidence "
                    f"and no related entry in contradictions.md."
                ),
            ))


def _has_related_contradiction(state, h) -> bool:
    htoks = set(h.title.lower().split())
    for c in state.contradictions.values():
        ctoks = set(c.title.lower().split()) | set(c.claim_a.lower().split())
        if htoks & ctoks:
            return True
    return False


def _check_missing_citations(findings, state) -> None:
    for h in state.hypotheses.values():
        for f in h.facts:
            if not re.search(r"Source:|Evidence:|raw_sources/|\[\[|claim_\d+|evt_\d+", f):
                findings.append(LintFinding(
                    rule="M3",
                    severity="Medium",
                    page="hypotheses.md",
                    message=(
                        f"Fact under '{h.title}' has no citation: '{f[:60]}...'."
                    ),
                ))
        if not h.supporting_evidence:
            findings.append(LintFinding(
                rule="M2",
                severity="Medium",
                page="hypotheses.md",
                message=f"Hypothesis '{h.title}' has no Supporting Evidence bullets.",
            ))


def _check_broken_wiki_links(findings, pages) -> None:
    page_basenames = {Path(name).stem for name in pages}
    page_basenames.update({"timeline", "entities", "iocs", "hypotheses",
                           "contradictions", "open_questions", "final_report",
                           "index"})
    for name, text in pages.items():
        for match in _WIKI_LINK_RE.finditer(text):
            target = match.group(1).strip()
            stem = Path(target).stem or target
            if stem not in page_basenames:
                findings.append(LintFinding(
                    rule="M5",
                    severity="Medium",
                    page=name,
                    message=f"Wiki link [[{target}]] does not resolve to a known page.",
                ))


def _check_contradictions_state_vs_page(findings, state, pages) -> None:
    """M6 — state.contradictions exists but contradictions.md misses it."""
    page = pages.get("contradictions.md", "")
    page_lower = page.lower()
    for c in state.contradictions.values():
        if c.title.lower() not in page_lower:
            findings.append(LintFinding(
                rule="M6",
                severity="Medium",
                page="contradictions.md",
                message=(
                    f"Contradiction '{c.title}' is in state but not rendered "
                    f"on contradictions.md (likely a hand-edit drift)."
                ),
            ))


_EXFIL_PHRASES = (
    "exfiltration occurred",
    "data was stolen",
    "data theft confirmed",
    "confirmed exfiltration",
)


def _check_exfiltration_overclaim(findings, state, pages) -> None:
    """C4 — wiki asserts exfiltration occurred without network/file-transfer evidence."""
    has_transfer_evidence = False
    for ev in state.events:
        d = ev.description.lower()
        if "outbound" in d or "transferred" in d or "uploaded" in d:
            has_transfer_evidence = True
            break
    # Even with transfer evidence, "exfiltration occurred" requires a
    # High/Confirmed hypothesis on the topic to be a defensible claim.
    strong = any(
        h.confidence in ("High", "Confirmed")
        and ("exfil" in h.title.lower() or "exfil" in h.inference.lower())
        for h in state.hypotheses.values()
    )
    if strong:
        return
    for name, text in pages.items():
        for raw_line in text.splitlines():
            line_lower = raw_line.lower()
            if _line_is_attributed(raw_line):
                continue
            for phrase in _EXFIL_PHRASES:
                if phrase in line_lower:
                    findings.append(LintFinding(
                        rule="C4",
                        severity="Critical",
                        page=name,
                        message=(
                            f"Page '{name}' asserts '{phrase}' without a "
                            f"High/Confirmed exfiltration hypothesis"
                            + ("; outbound activity is recorded but transfer "
                               "alone does not confirm exfiltration."
                               if has_transfer_evidence else
                               "; no transfer-shaped evidence is recorded.")
                        ),
                    ))
                    break


def _check_final_report_claims_match_index(findings, project_root, case_id, pages) -> None:
    """H4 — every claim_NNNN referenced in final_report.md must exist in claims.json."""
    fr = pages.get("final_report.md", "")
    if not fr:
        return
    referenced = set(re.findall(r"\bclaim_\d{4}\b", fr))
    if not referenced:
        return
    import json
    cj = project_root / "wiki" / "cases" / case_id / ".fw" / "claims.json"
    if not cj.exists():
        return
    known = {c.get("claim_id") for c in json.loads(cj.read_text())}
    for cid in sorted(referenced - known):
        findings.append(LintFinding(
            rule="H4",
            severity="High",
            page="final_report.md",
            message=(
                f"final_report.md references {cid} but it is not present in "
                f".fw/claims.json. Either the report is stale or the claim was removed."
            ),
        ))


def _check_suggest_review_mode(findings) -> None:
    """C5 — if any Critical finding is present, add a meta-finding pointing the
    user at ``--review`` mode for the next ingest/report."""
    if any(f.severity == "Critical" for f in findings):
        findings.append(LintFinding(
            rule="C5",
            severity="Critical",
            page="(meta)",
            message=(
                "Critical findings detected. Consider re-running ingest/report "
                "with --review so risky wiki updates are held for human approval "
                "instead of applied automatically."
            ),
        ))


def _check_stale_pages(findings, project_root, case_id, manifest) -> None:
    """M4 — a page's mtime predates the last ingest run."""
    if not manifest.last_ingest_at:
        return
    try:
        cutoff = _dt.datetime.fromisoformat(manifest.last_ingest_at.rstrip("Z"))
    except ValueError:
        return
    cdir = case_dir(project_root, case_id)
    for name in REQUIRED_PAGES:
        p = cdir / name
        if not p.exists():
            continue
        mtime = _dt.datetime.utcfromtimestamp(p.stat().st_mtime)
        # 5-second slack avoids false positives on the same-run rendering.
        if mtime + _dt.timedelta(seconds=5) < cutoff:
            findings.append(LintFinding(
                rule="M4",
                severity="Medium",
                page=name,
                message=(
                    f"Page '{name}' was last modified before the most recent "
                    f"ingest run ({manifest.last_ingest_at}); may be stale."
                ),
            ))


# --------------------------------------------------------------------------- #
# Low rules
# --------------------------------------------------------------------------- #


_COMPATIBLE_DUP_TYPES = frozenset({"file", "process", "command"})


def _check_duplicate_entities(findings, state) -> None:
    seen_values: dict[str, list[tuple[str, str]]] = {}
    for key, e in state.entities.items():
        seen_values.setdefault(e.value.lower(), []).append((e.type, key))
    for value, items in seen_values.items():
        if len(items) <= 1:
            continue
        types = {t for t, _ in items}
        if types <= _COMPATIBLE_DUP_TYPES:
            continue
        keys = ", ".join(k for _, k in items)
        findings.append(LintFinding(
            rule="L1",
            severity="Low",
            page="entities.md",
            message=(
                f"Value '{value}' appears under multiple entity types: "
                f"{keys}. Verify they truly differ."
            ),
        ))


def _check_orphan_pages(findings, pages) -> None:
    linked: set[str] = set()
    for text in pages.values():
        for m in _WIKI_LINK_RE.finditer(text):
            linked.add(Path(m.group(1).strip()).stem)
    for name in pages:
        stem = Path(name).stem
        if stem in {"index"}:
            continue
        if stem not in linked:
            findings.append(LintFinding(
                rule="L2",
                severity="Low",
                page=name,
                message=f"Page '{name}' is not linked from any other page.",
            ))


def _check_orphan_entities(findings, state, pages) -> None:
    other_pages_text = " ".join(
        text for name, text in pages.items() if name not in {"entities.md"}
    ).lower()
    for _key, e in state.entities.items():
        if e.value.lower() not in other_pages_text:
            findings.append(LintFinding(
                rule="L3",
                severity="Low",
                page="entities.md",
                message=(
                    f"Entity '{e.heading}' is defined but not referenced by "
                    f"any other page."
                ),
            ))


def _check_ioc_cross_refs(findings, state) -> None:
    for ioc in state.iocs.values():
        if not ioc.related:
            findings.append(LintFinding(
                rule="L5",
                severity="Low",
                page="iocs.md",
                message=f"IOC '{ioc.artifact}' has no Related cross-reference.",
            ))


# --------------------------------------------------------------------------- #
# Formatting
# --------------------------------------------------------------------------- #


def format_report(report: LintReport) -> str:
    if report.is_clean():
        return "Lint: clean. 0 findings."
    lines: list[str] = []
    for sev in ("Critical", "High", "Medium", "Low"):
        items = report.by_severity(sev)  # type: ignore[arg-type]
        if not items:
            continue
        lines.append(f"{sev.upper()}:")
        for f in items:
            lines.append(f"- [{f.rule}] {f.message} ({f.page})")
        lines.append("")
    summary = report.summary()
    lines.append(
        f"Summary: critical={summary['critical']} high={summary['high']} "
        f"medium={summary['medium']} low={summary['low']}"
    )
    return "\n".join(lines).rstrip()


def format_json(report: LintReport) -> str:
    return json.dumps({
        "case_id": report.case_id,
        "generated_at": report.generated_at,
        "summary": report.summary(),
        "findings": [
            {"rule": f.rule, "severity": f.severity, "page": f.page, "message": f.message}
            for f in report.findings
        ],
    }, indent=2)
