"""Lint must catch overconfident language and missing citations even when
the underlying state has been hand-edited."""
from __future__ import annotations

from pathlib import Path

from src.ingest import ingest_case
from src.lint import lint_case
from src.schemas import Citation, Hypothesis
from src.wiki_io import case_dir, load_state, render_all_pages, save_state


def test_lint_clean_after_fresh_ingest_has_no_high_findings(project: Path) -> None:
    ingest_case(project, "case_001")
    report = lint_case(project, "case_001")
    assert not report.by_severity("Critical"), "fresh ingest should not raise Critical findings"
    assert not report.by_severity("High"), "fresh ingest should not raise High findings"


def test_lint_flags_confirmed_malware_overclaim(project: Path) -> None:
    ingest_case(project, "case_001")
    cdir = case_dir(project, "case_001")
    fr = cdir / "final_report.md"
    fr.write_text(fr.read_text() + "\n\n## Verdict\n\nThis is confirmed malware.\n")

    report = lint_case(project, "case_001")
    rules = {f.rule for f in report.by_severity("Critical")}
    assert "C1" in rules or "C2" in rules


def test_lint_flags_missing_citation(project: Path) -> None:
    ingest_case(project, "case_001")
    state = load_state(project, "case_001")
    state.hypotheses["uncited"] = Hypothesis(
        title="Uncited Hypothesis",
        confidence="Medium",
        facts=["Something happened without a citation"],
        inference="This is unsourced",
        supporting_evidence=[],
        contradicting_evidence=[],
    )
    save_state(project, state)
    render_all_pages(project, state)

    report = lint_case(project, "case_001")
    rules = {f.rule for f in report.findings}
    assert "M3" in rules


def test_lint_flags_broken_raw_citation(project: Path) -> None:
    ingest_case(project, "case_001")
    cdir = case_dir(project, "case_001")
    iocs = cdir / "iocs.md"
    iocs.write_text(
        iocs.read_text()
        + "\n\n_Manual annotation: see raw_sources/case_001/ghost_file.txt for details._\n"
    )
    report = lint_case(project, "case_001")
    assert any(f.rule == "C3" for f in report.findings)


def test_lint_flags_missing_required_page(project: Path) -> None:
    ingest_case(project, "case_001")
    (case_dir(project, "case_001") / "contradictions.md").unlink()
    report = lint_case(project, "case_001")
    assert any(f.rule == "H1" for f in report.findings)


def test_lint_flags_hypothesis_with_no_supporting_evidence(project: Path) -> None:
    ingest_case(project, "case_001")
    state = load_state(project, "case_001")
    state.hypotheses["dangling"] = Hypothesis(
        title="Dangling Inference",
        confidence="Low",
        facts=[],
        inference="A wild guess unsupported by any fact.",
        supporting_evidence=[],
        contradicting_evidence=["Source: raw_sources/case_001/defender_scan.txt"],
    )
    save_state(project, state)
    render_all_pages(project, state)

    report = lint_case(project, "case_001")
    assert any(f.rule == "M2" for f in report.findings)
