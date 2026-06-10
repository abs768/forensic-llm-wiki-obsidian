"""Benchmark: wiki vs raw-source RAG, deterministic scoring, JSON+MD output."""
from __future__ import annotations

import json
from pathlib import Path

from src.benchmark import benchmark_case
from src.evolve import benchmark_case_dir, evolve_case


def _setup(project: Path) -> None:
    evolve_case(project, "case_002_evolving")


def test_benchmark_writes_results_md_and_json(project: Path) -> None:
    _setup(project)
    summary = benchmark_case(project, "case_002_evolving")
    out = benchmark_case_dir(project, "case_002_evolving")
    assert (out / "results.md").exists()
    assert (out / "results.json").exists()
    assert summary.total >= 15


def test_benchmark_wiki_beats_raw_rag_overall(project: Path) -> None:
    _setup(project)
    summary = benchmark_case(project, "case_002_evolving")
    assert summary.wiki_passed > summary.rag_passed, (
        f"wiki={summary.wiki_passed} rag={summary.rag_passed}"
    )


def test_benchmark_wiki_wins_on_contradiction_detection(project: Path) -> None:
    _setup(project)
    summary = benchmark_case(project, "case_002_evolving")
    assert summary.wiki_contradiction_misses < summary.rag_contradiction_misses, (
        f"wiki misses={summary.wiki_contradiction_misses} "
        f"rag misses={summary.rag_contradiction_misses}"
    )


def test_benchmark_wiki_wins_on_refusal(project: Path) -> None:
    _setup(project)
    summary = benchmark_case(project, "case_002_evolving")
    assert summary.wiki_refusal_accuracy > summary.rag_refusal_accuracy


def test_benchmark_results_json_is_parseable(project: Path) -> None:
    _setup(project)
    benchmark_case(project, "case_002_evolving")
    blob = (benchmark_case_dir(project, "case_002_evolving") / "results.json").read_text()
    data = json.loads(blob)
    assert data["case_id"] == "case_002_evolving"
    assert "rows" in data
    assert all("wiki_passed" in row and "rag_passed" in row for row in data["rows"])


def test_benchmark_results_md_contains_scoring_table(project: Path) -> None:
    _setup(project)
    benchmark_case(project, "case_002_evolving")
    text = (benchmark_case_dir(project, "case_002_evolving") / "results.md").read_text()
    assert "Raw RAG" in text and "LLM Wiki" in text
    assert "Refusal accuracy" in text
    assert "Contradiction misses" in text


def test_benchmark_runs_without_real_api_key(project: Path, monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("FORENSIC_WIKI_LLM", "mock")
    _setup(project)
    summary = benchmark_case(project, "case_002_evolving")
    assert summary.total >= 15
