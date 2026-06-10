"""Eval runner."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from src.eval import format_summary, load_eval_file, run_eval
from src.ingest import ingest_case

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _copy_eval(project: Path) -> None:
    (project / "evals").mkdir(parents=True, exist_ok=True)
    shutil.copy(
        PROJECT_ROOT / "evals" / "case_001_eval.json",
        project / "evals" / "case_001_eval.json",
    )


def test_eval_file_loads(project: Path) -> None:
    _copy_eval(project)
    cases = load_eval_file(project, "case_001")
    assert len(cases) >= 4
    q1 = cases[0]
    assert q1.id == "q001"
    assert q1.expect_refusal is True


def test_eval_passes_on_well_ingested_case(project: Path) -> None:
    _copy_eval(project)
    ingest_case(project, "case_001")
    summary = run_eval(project, "case_001")
    assert summary.total >= 4
    # Allow some tolerance: at least 3 of 4 questions should pass.
    assert summary.passed >= 3, format_summary(summary, verbose=True)


def test_eval_catches_must_not_include_violation(project: Path) -> None:
    _copy_eval(project)
    ingest_case(project, "case_001")
    # Sabotage final_report.md so the generated answer is unchanged, but
    # construct a bespoke eval that forces a must_not_include failure to
    # exercise the runner.
    eval_path = project / "evals" / "case_001_eval.json"
    payload = {
        "case_id": "case_001",
        "items": [{
            "id": "q_sabotage",
            "question": "What evidence supports persistence?",
            "must_include": ["DeskRest"],
            "must_not_include": ["DeskRest"],  # guaranteed failure
            "required_sources": [],
            "expect_refusal": False,
            "expect_separation": False,
        }],
    }
    eval_path.write_text(json.dumps(payload))
    summary = run_eval(project, "case_001")
    assert summary.failed == 1
    assert summary.unsupported_claim_failures == 1


def test_eval_catches_missing_required_source(project: Path) -> None:
    _copy_eval(project)
    ingest_case(project, "case_001")
    eval_path = project / "evals" / "case_001_eval.json"
    payload = {
        "case_id": "case_001",
        "items": [{
            "id": "q_missing",
            "question": "What evidence supports persistence?",
            "must_include": [],
            "must_not_include": [],
            "required_sources": ["nonexistent_file_xyz.bin"],
            "expect_refusal": False,
            "expect_separation": False,
        }],
    }
    eval_path.write_text(json.dumps(payload))
    summary = run_eval(project, "case_001")
    assert summary.failed == 1
    assert summary.missing_source_failures == 1


def test_format_summary_shows_counts(project: Path) -> None:
    _copy_eval(project)
    ingest_case(project, "case_001")
    summary = run_eval(project, "case_001")
    text = format_summary(summary)
    assert "Total:" in text
    assert "Passed:" in text
    assert "Failed:" in text
