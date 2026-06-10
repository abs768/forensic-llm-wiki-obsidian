"""Dry-run computes diffs without touching the filesystem."""
from __future__ import annotations

from pathlib import Path

from src.ingest import format_dry_run, ingest_case
from src.wiki_io import case_dir


def test_dry_run_does_not_create_wiki_files(project: Path) -> None:
    report = ingest_case(project, "case_001", dry_run=True)
    cdir = case_dir(project, "case_001")
    assert report.dry_run is True
    assert report.pages_written == []
    # Nothing should have been written.
    assert not (cdir / "timeline.md").exists()
    assert not (cdir / ".fw" / "state.json").exists()
    assert not (cdir / ".fw" / "manifest.json").exists()


def test_dry_run_reports_pages_that_would_change(project: Path) -> None:
    report = ingest_case(project, "case_001", dry_run=True)
    assert "timeline.md" in report.pages_changed
    assert "hypotheses.md" in report.pages_changed
    # Diff is non-empty for new file.
    assert report.page_diffs["timeline.md"]


def test_dry_run_diff_contains_unified_format(project: Path) -> None:
    report = ingest_case(project, "case_001", dry_run=True)
    diff = report.page_diffs["hypotheses.md"]
    assert "+++ b/hypotheses.md" in diff
    assert "Possible Registry-Based Persistence" in diff


def test_format_dry_run_includes_would_update_label(project: Path) -> None:
    report = ingest_case(project, "case_001", dry_run=True)
    text = format_dry_run(report)
    assert "Would update" in text
    assert "case_001" in text


def test_dry_run_then_apply_writes_files(project: Path) -> None:
    ingest_case(project, "case_001", dry_run=True)
    # Real ingest after dry-run still processes everything.
    report = ingest_case(project, "case_001")
    assert report.sources_processed
    assert (case_dir(project, "case_001") / "timeline.md").exists()
    assert (case_dir(project, "case_001") / ".fw" / "state.json").exists()
