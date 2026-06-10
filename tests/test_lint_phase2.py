"""Phase 2 lint rules: severity tiers, never-ingested, weak-high-confidence,
JSON output."""
from __future__ import annotations

import json
from pathlib import Path

from src.ingest import ingest_case
from src.lint import format_json, lint_case
from src.schemas import Hypothesis
from src.wiki_io import load_state, render_all_pages, save_state


def test_lint_critical_on_confirmed_malware_phrase(project: Path) -> None:
    ingest_case(project, "case_001")
    cdir = project / "wiki" / "cases" / "case_001"
    fr = cdir / "final_report.md"
    fr.write_text(fr.read_text() + "\n\n## Verdict\n\nThis is confirmed malware.\n")
    report = lint_case(project, "case_001")
    critical = report.by_severity("Critical")
    assert critical, "confirmed-malware overclaim must be Critical"
    assert any(f.rule in {"C1", "C2"} for f in critical)


def test_lint_high_on_raw_source_never_ingested(project: Path) -> None:
    ingest_case(project, "case_001")
    # Drop a new file into raw_sources that the manifest has never seen.
    new = project / "raw_sources" / "case_001" / "unseen.txt"
    new.write_text("brand-new evidence\n")
    report = lint_case(project, "case_001")
    rules = {f.rule for f in report.by_severity("High")}
    assert "H2" in rules


def test_lint_high_on_high_confidence_weak_evidence(project: Path) -> None:
    ingest_case(project, "case_001")
    state = load_state(project, "case_001")
    state.hypotheses["weak-high"] = Hypothesis(
        title="Weak High Hypothesis",
        confidence="High",
        facts=["Some fact (Source: raw_sources/case_001/powershell_history.txt)"],
        inference="A claim with only one supporting bullet.",
        supporting_evidence=["Source: raw_sources/case_001/powershell_history.txt"],
        contradicting_evidence=["Source: raw_sources/case_001/defender_scan.txt"],
    )
    save_state(project, state)
    render_all_pages(project, state)
    report = lint_case(project, "case_001")
    assert any(f.rule == "H3" for f in report.findings)


def test_lint_json_output(project: Path) -> None:
    ingest_case(project, "case_001")
    report = lint_case(project, "case_001")
    blob = format_json(report)
    data = json.loads(blob)
    assert data["case_id"] == "case_001"
    assert "summary" in data
    assert set(data["summary"].keys()) == {"critical", "high", "medium", "low"}
    assert "findings" in data
    for f in data["findings"]:
        assert f["rule"]
        assert f["severity"] in {"Critical", "High", "Medium", "Low"}


def test_lint_summary_counts_match_findings(project: Path) -> None:
    ingest_case(project, "case_001")
    report = lint_case(project, "case_001")
    summary = report.summary()
    for sev_lower, sev_title in [("critical", "Critical"), ("high", "High"),
                                  ("medium", "Medium"), ("low", "Low")]:
        assert summary[sev_lower] == len(report.by_severity(sev_title))
