"""Snapshot + diff-snapshots command."""
from __future__ import annotations

from pathlib import Path

from src.evolve import evolve_case
from src.snapshots import diff_snapshots, format_diff, list_snapshots, take_snapshot


def test_take_snapshot_after_single_ingest(project: Path) -> None:
    from src.ingest import ingest_case
    ingest_case(project, "case_001")
    snap = take_snapshot(project, "case_001", "manual_test")
    assert snap.exists()
    assert (snap / "timeline.md").exists()
    assert (snap / ".fw" / "state.json").exists()


def test_diff_snapshots_returns_changes_between_steps(project: Path) -> None:
    evolve_case(project, "case_002_evolving")
    snaps = list_snapshots(project, "case_002_evolving")
    # Compare step 02 (registry) with step 03 (defender clean scan).
    s2 = next(s for s in snaps if "step_02_registry" in s)
    s3 = next(s for s in snaps if "step_03_defender" in s)
    diffs = diff_snapshots(project, "case_002_evolving", s2, s3)
    assert diffs, "expected at least one page to change between step 02 and 03"
    # contradictions.md or hypotheses.md should reflect the Defender clean
    # scan vs persistence contradiction.
    assert "contradictions.md" in diffs or "hypotheses.md" in diffs


def test_diff_snapshots_identical_returns_empty(project: Path) -> None:
    evolve_case(project, "case_002_evolving")
    snaps = list_snapshots(project, "case_002_evolving")
    diffs = diff_snapshots(project, "case_002_evolving", snaps[0], snaps[0])
    assert diffs == {}


def test_diff_format_includes_page_change_header(project: Path) -> None:
    evolve_case(project, "case_002_evolving")
    snaps = list_snapshots(project, "case_002_evolving")
    diffs = diff_snapshots(project, "case_002_evolving", snaps[0], snaps[1])
    text = format_diff("case_002_evolving", snaps[0], snaps[1], diffs)
    assert "Diff: case_002_evolving" in text
    assert "--- Page changed:" in text
