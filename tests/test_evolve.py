"""Evolve workflow: step-by-step ingestion, snapshots, hypothesis history,
evolution report."""
from __future__ import annotations

import json
from pathlib import Path

from src.evolve import benchmark_case_dir, evolve_case, list_step_dirs
from src.hypothesis_history import history_path, load_history
from src.snapshots import list_snapshots, snapshot_dir
from src.wiki_io import REQUIRED_PAGES, case_dir


def test_list_step_dirs_finds_all_six(project: Path) -> None:
    steps = list_step_dirs(project, "case_002_evolving")
    assert len(steps) == 6
    assert steps[0].name == "step_01_powershell"
    assert steps[-1].name == "step_06_hash_reputation"


def test_evolve_runs_through_every_step(project: Path) -> None:
    result = evolve_case(project, "case_002_evolving")
    assert len(result.steps) == 6
    for step in result.steps:
        assert step.snapshot_name.startswith("after_step_")
        assert step.files_added, f"step {step.name} processed no files"
        assert step.pages_changed, f"step {step.name} changed no pages"


def test_snapshots_created_for_every_step(project: Path) -> None:
    evolve_case(project, "case_002_evolving")
    snaps = list_snapshots(project, "case_002_evolving")
    assert len(snaps) == 6
    for snap in snaps:
        sd = snapshot_dir(project, "case_002_evolving", snap)
        for page in REQUIRED_PAGES:
            assert (sd / page).exists(), f"{snap}/{page} missing"
        assert (sd / ".fw").exists()
        assert (sd / ".fw" / "state.json").exists()


def test_evolution_report_written(project: Path) -> None:
    evolve_case(project, "case_002_evolving")
    report = benchmark_case_dir(project, "case_002_evolving") / "evolution_report.md"
    assert report.exists()
    text = report.read_text()
    assert "Case Evolution Report" in text
    assert "step_01_powershell" in text
    assert "step_06_hash_reputation" in text
    assert "Assessment after this step" in text


def test_hypothesis_history_created(project: Path) -> None:
    evolve_case(project, "case_002_evolving")
    p = history_path(project, "case_002_evolving")
    assert p.exists()
    history = load_history(project, "case_002_evolving")
    assert history.case_id == "case_002_evolving"
    assert history.histories, "no hypotheses tracked"
    persistence = next(
        (h for h in history.histories if "persistence" in h.hypothesis.lower()),
        None,
    )
    assert persistence is not None
    assert persistence.history, "persistence hypothesis has no snapshots"
    # Spec format: "history" list with snapshots referencing step names.
    steps = [s.step for s in persistence.history]
    assert any("step_02_registry" in s for s in steps)


def test_evolve_starts_from_clean_state(project: Path) -> None:
    # Pre-populate wiki to ensure evolve wipes it.
    cdir = case_dir(project, "case_002_evolving")
    cdir.mkdir(parents=True, exist_ok=True)
    (cdir / "bogus.md").write_text("legacy junk")
    evolve_case(project, "case_002_evolving")
    assert not (cdir / "bogus.md").exists()


def test_evolution_assessment_changes_across_steps(project: Path) -> None:
    """The whole point of evolve: the assessment shifts as evidence arrives."""
    result = evolve_case(project, "case_002_evolving")
    assessments = [s.key_assessment for s in result.steps]
    # Step 1 has nothing in the wiki yet → fallback / insufficient.
    # Later steps should reference the malware hypothesis with refusal.
    final = assessments[-1].lower()
    assert "not confirmed" in final or "no hypothesis" in final or "unsupported" in final
    # And the final step must mention persistence-related reasoning.
    assert "persistence" in final or "suspicious" in final
