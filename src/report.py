"""Report operation.

Compiles ``final_report.md`` from the case's structured state. The report
draft preserves the fact / inference / hypothesis distinction and never
elevates a hypothesis above its actual confidence.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .review import create_review, scan_for_risky_phrases
from .wiki_io import WikiState, case_dir, load_state


def generate_report(
    project_root: Path,
    case_id: str,
    *,
    review: bool = False,
) -> str:
    """Generate the final-report draft and return its body.

    Default mode overwrites ``final_report.md`` directly. With
    ``review=True``, if the proposed body contains risky phrases
    (e.g. ``"confirmed malware"``) the file is **not** written; instead a
    review item is queued. Callers in review mode can detect that the
    item was queued via the review-queue API.
    """
    state = load_state(project_root, case_id)
    body = _render(state)
    cdir = case_dir(project_root, case_id)
    cdir.mkdir(parents=True, exist_ok=True)
    target = cdir / "final_report.md"

    if review:
        risky = scan_for_risky_phrases(body)
        if risky:
            prior = target.read_text() if target.exists() else ""
            create_review(
                project_root, case_id,
                change_type="report_update",
                target_page="final_report.md",
                proposed_content=body,
                prior_content=prior,
                reason=(
                    f"Proposed final_report.md contains risky phrase(s) {risky!r}; "
                    f"held for human review."
                ),
                risky_phrases=risky,
            )
            return body

    target.write_text(body)
    return body


def _render(state: WikiState) -> str:
    updated = state.last_updated or datetime.utcnow().isoformat(timespec="seconds") + "Z"
    lines: list[str] = []
    lines.append("---")
    lines.append(f"case: {state.case_id}")
    lines.append("page: final_report")
    lines.append(f"updated: {updated}")
    lines.append(f"sources: {state.source_count()}")
    lines.append("---\n")

    lines.append(f"# Final Report — Case {state.case_id}\n")
    lines.append(
        "> This draft separates **facts** (observed in raw sources), "
        "**inferences** (derived reasoning), and **hypotheses** (proposed "
        "explanations). Hypotheses must not be promoted to facts without "
        "strong, independent evidence."
    )
    lines.append("")

    lines.append("## Executive Summary\n")
    lines.append(_executive_summary(state))
    lines.append("")

    lines.append("## Timeline\n")
    if not state.events:
        lines.append("_no events_")
    else:
        for ev in sorted(state.events, key=lambda e: (0 if e.timestamp != "unknown" else 1, e.timestamp)):
            lines.append(f"- **{ev.timestamp or 'unknown'}** — {ev.description} ({ev.citation.target})")
    lines.append("")

    lines.append("## Key Artifacts\n")
    file_entities = [e for e in state.entities.values() if e.type == "file"]
    if file_entities:
        for e in sorted(file_entities, key=lambda e: e.value):
            lines.append(f"- {e.value}")
    else:
        lines.append("- _none_")
    lines.append("")

    lines.append("## Indicators of Compromise\n")
    if not state.iocs:
        lines.append("- _none_")
    for ioc in sorted(state.iocs.values(), key=lambda i: i.artifact):
        lines.append(
            f"- {ioc.artifact} ({ioc.type}, confidence: {ioc.confidence}) — "
            f"{ioc.reason} (Source: {ioc.source})"
        )
    lines.append("")

    lines.append("## Hypotheses\n")
    if not state.hypotheses:
        lines.append("- _none_")
    for h in sorted(state.hypotheses.values(), key=lambda h: h.title):
        lines.append(f"### {h.title} (confidence: {h.confidence})\n")
        lines.append("**Facts**")
        for f in h.facts or ["_none_"]:
            lines.append(f"- {f}")
        lines.append("")
        lines.append("**Inference**")
        lines.append(h.inference or "_none_")
        lines.append("")
        lines.append("**Supporting Evidence**")
        for s in h.supporting_evidence or ["_none_"]:
            lines.append(f"- {s}")
        lines.append("")
        lines.append("**Contradicting Evidence**")
        if h.contradicting_evidence:
            for c in h.contradicting_evidence:
                lines.append(f"- {c}")
        else:
            lines.append("- See Contradictions section for related conflicts.")
        lines.append("")

    lines.append("## Contradictions\n")
    if not state.contradictions:
        lines.append("- _none_")
    for contra in sorted(state.contradictions.values(), key=lambda c: c.title):
        lines.append(
            f"- **{contra.title}** — Claim A: {contra.claim_a} / "
            f"Claim B: {contra.claim_b} ({contra.status})"
        )
    lines.append("")

    lines.append("## Recommended Next Steps\n")
    next_steps = _dedupe([s for h in state.hypotheses.values() for s in h.next_steps])
    if next_steps:
        for s in next_steps:
            lines.append(f"- {s}")
    else:
        lines.append("- _none_")
    lines.append("")

    lines.append("## Appendix: Sources\n")
    for src in sorted(state.source_files):
        lines.append(f"- {src}")
    lines.append("")
    return "\n".join(lines)


def _executive_summary(state: WikiState) -> str:
    if not state.hypotheses:
        return "No hypotheses have been formed yet. No firm conclusions can be drawn."
    rank = {"Low": 1, "Medium": 2, "High": 3, "Confirmed": 4}
    top = max(state.hypotheses.values(), key=lambda h: rank.get(h.confidence, 0))
    base = (
        f"Strongest open hypothesis: **{top.title}** "
        f"(confidence: {top.confidence}). {top.inference}"
    )
    if state.contradictions:
        base += (
            f" Note: {len(state.contradictions)} active contradiction(s) "
            f"prevent stronger claims."
        )
    base += (
        " This report draft does **not** confirm malware, exfiltration, or "
        "compromise unless an associated hypothesis is rated High or "
        "Confirmed."
    )
    return base


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for s in items:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out
