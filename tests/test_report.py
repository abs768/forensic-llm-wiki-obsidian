"""Final report must keep facts, inferences, and hypotheses separate and
must never escalate hypotheses into confirmed conclusions."""
from __future__ import annotations

from pathlib import Path

from src.ingest import ingest_case
from src.report import generate_report


def test_report_separates_facts_and_hypotheses(project: Path) -> None:
    ingest_case(project, "case_001")
    body = generate_report(project, "case_001")

    # The required section headers must exist and the facts/inference
    # distinction must survive.
    assert "## Executive Summary" in body
    assert "## Timeline" in body
    assert "## Key Artifacts" in body
    assert "## Indicators of Compromise" in body
    assert "## Hypotheses" in body
    assert "## Contradictions" in body
    assert "## Recommended Next Steps" in body
    assert "## Appendix: Sources" in body
    assert "**Facts**" in body
    assert "**Inference**" in body


def test_report_does_not_confirm_malware(project: Path) -> None:
    ingest_case(project, "case_001")
    body = generate_report(project, "case_001").lower()
    assert "confirmed malware" not in body
    assert "malware confirmed" not in body
    assert "definitely malicious" not in body


def test_report_writes_to_final_report_path(project: Path) -> None:
    ingest_case(project, "case_001")
    generate_report(project, "case_001")
    fr = project / "wiki" / "cases" / "case_001" / "final_report.md"
    assert fr.exists()
    assert "Final Report" in fr.read_text()


def test_report_includes_sources_appendix(project: Path) -> None:
    ingest_case(project, "case_001")
    body = generate_report(project, "case_001")
    assert "raw_sources/case_001/powershell_history.txt" in body
    assert "raw_sources/case_001/defender_scan.txt" in body
