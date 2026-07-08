"""Phase 5: GraphRAG-lite baseline, multi-method compare/benchmark, and the
positioning docs/README.

All tests run in mock-LLM mode.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from src.benchmark_methods import METHODS, benchmark_methods
from src.compare_all import compare_all, format_all_methods
from src.evolve import benchmark_case_dir, evolve_case
from src.graph import build_graph, save_graph, to_mermaid
from src.graph.graph_builder import graph_md_path, graph_mmd_path, graph_path
from src.graph.graph_query import graph_query

REPO_ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------- #
# graph-build / graph.json / graph.md / graph.mmd
# --------------------------------------------------------------------------- #


def _evolve_and_graph(project: Path) -> None:
    evolve_case(project, "case_002_evolving")
    save_graph(project, build_graph(project, "case_002_evolving"))


def test_graph_json_created(project: Path) -> None:
    _evolve_and_graph(project)
    p = graph_path(project, "case_002_evolving")
    assert p.exists()
    data = json.loads(p.read_text())
    assert data["case_id"] == "case_002_evolving"
    assert data["nodes"]
    assert data["edges"]


def test_graph_md_created_with_node_and_edge_summary(project: Path) -> None:
    _evolve_and_graph(project)
    md = graph_md_path(project, "case_002_evolving").read_text()
    assert "Relationship Graph" in md
    assert "Nodes by type" in md
    assert "Edges by type" in md


def test_graph_has_expected_node_types(project: Path) -> None:
    _evolve_and_graph(project)
    data = json.loads(graph_path(project, "case_002_evolving").read_text())
    types = {n["type"] for n in data["nodes"]}
    # The demo case exercises these kinds at minimum.
    assert "file" in types
    assert "source" in types
    assert "registry_key" in types
    assert "ip_address" in types
    assert "hypothesis" in types


def test_graph_has_expected_edge_types(project: Path) -> None:
    _evolve_and_graph(project)
    data = json.loads(graph_path(project, "case_002_evolving").read_text())
    edge_types = {e["type"] for e in data["edges"]}
    # mentioned_in and related_to should always appear from entities; the
    # rest depend on the demo case's specific events.
    assert "mentioned_in" in edge_types
    assert "related_to" in edge_types
    assert {"supports", "contradicts"} & edge_types


def test_graph_query_returns_related_entities(project: Path) -> None:
    _evolve_and_graph(project)
    ans = graph_query(project, "case_002_evolving",
                      "What is DeskRest.exe related to?")
    assert not ans.insufficient
    text = ans.answer.lower()
    # Graph query should list at least the registry and a source file.
    assert "registry" in text or "registry_run_keys" in text
    assert "powershell" in text or "deskrest" in text


def test_graph_query_refuses_off_graph_questions(project: Path) -> None:
    _evolve_and_graph(project)
    ans = graph_query(project, "case_002_evolving",
                      "Is this confirmed malware?")
    # No specific entity matched, so the graph shouldn't claim an answer.
    assert ans.insufficient is True


def test_graph_mermaid_export(project: Path) -> None:
    _evolve_and_graph(project)
    graph = build_graph(project, "case_002_evolving")
    text = to_mermaid(graph)
    assert text.startswith("graph TD")
    # Must contain at least one styled node and one labelled edge.
    assert "[\"" in text
    assert "-->|" in text


def test_graph_mmd_written_to_disk(project: Path) -> None:
    _evolve_and_graph(project)
    p = graph_mmd_path(project, "case_002_evolving")
    assert p.exists()
    assert p.read_text().startswith("graph TD")


# --------------------------------------------------------------------------- #
# compare-all
# --------------------------------------------------------------------------- #


def test_compare_all_includes_all_methods(project: Path) -> None:
    _evolve_and_graph(project)
    result = compare_all(project, "case_002_evolving",
                         "Is this confirmed malware?")
    # All five providers must produce a QueryAnswer.
    assert result.raw_rag.question
    assert result.vector_rag.question
    assert result.graph_rag_lite.question
    assert result.llm_wiki.question
    assert result.hybrid.question
    out = format_all_methods(result)
    for label in ("Raw RAG", "Vector RAG", "GraphRAG-lite", "LLM Wiki", "Hybrid"):
        assert label in out


def test_hybrid_answer_combines_wiki_and_graph(project: Path) -> None:
    _evolve_and_graph(project)
    result = compare_all(project, "case_002_evolving",
                         "Explain the evidence chain and current assessment for DeskRest.exe.")
    text = result.hybrid.answer.lower()
    # Wiki side surfaces refusal / persistence; graph side surfaces relationships.
    assert "not confirmed" in text or "persistence" in text
    assert "relationship" in text or "graph" in text


# --------------------------------------------------------------------------- #
# benchmark-methods
# --------------------------------------------------------------------------- #


def test_benchmark_methods_writes_md_and_json(project: Path) -> None:
    _evolve_and_graph(project)
    summary = benchmark_methods(project, "case_002_evolving")
    out = benchmark_case_dir(project, "case_002_evolving")
    assert (out / "method_comparison.md").exists()
    assert (out / "method_comparison.json").exists()
    assert summary.total >= 15
    for method in METHODS:
        assert method in summary.per_method
        per = summary.per_method[method]
        for key in ("passed", "failed", "unsupported_failures",
                    "missing_source_failures", "refusal_accuracy",
                    "contradiction_misses", "relationship_coverage",
                    "narrative_state_quality", "expected_best_wins"):
            assert key in per


def test_graph_beats_raw_rag_on_relationship_coverage(project: Path) -> None:
    """Either GraphRAG-lite or Hybrid must beat Raw RAG on relationship_coverage."""
    _evolve_and_graph(project)
    summary = benchmark_methods(project, "case_002_evolving")
    rag = summary.per_method["raw_rag"]["relationship_coverage"]
    graph = summary.per_method["graph_rag_lite"]["relationship_coverage"]
    hybrid = summary.per_method["hybrid"]["relationship_coverage"]
    assert hybrid >= graph >= rag or hybrid > rag, (
        f"rag={rag} graph={graph} hybrid={hybrid}"
    )
    # The hybrid line is the more reliable demonstration that graph
    # context lifts the answer.
    assert hybrid > rag


def test_llm_wiki_beats_graph_on_refusal(project: Path) -> None:
    _evolve_and_graph(project)
    summary = benchmark_methods(project, "case_002_evolving")
    wiki = summary.per_method["llm_wiki"]["refusal_accuracy"]
    graph = summary.per_method["graph_rag_lite"]["refusal_accuracy"]
    assert wiki > graph, f"wiki refusal={wiki} graph refusal={graph}"


def test_llm_wiki_beats_graph_on_contradiction_misses(project: Path) -> None:
    _evolve_and_graph(project)
    summary = benchmark_methods(project, "case_002_evolving")
    wiki = summary.per_method["llm_wiki"]["contradiction_misses"]
    graph = summary.per_method["graph_rag_lite"]["contradiction_misses"]
    assert wiki <= graph, f"wiki misses={wiki} graph misses={graph}"


def test_hybrid_is_at_least_as_good_as_components_overall(project: Path) -> None:
    _evolve_and_graph(project)
    summary = benchmark_methods(project, "case_002_evolving")
    hybrid_passed = summary.per_method["hybrid"]["passed"]
    wiki_passed = summary.per_method["llm_wiki"]["passed"]
    graph_passed = summary.per_method["graph_rag_lite"]["passed"]
    assert hybrid_passed >= wiki_passed
    assert hybrid_passed >= graph_passed


# --------------------------------------------------------------------------- #
# Docs / README
# --------------------------------------------------------------------------- #


def test_why_llm_wiki_doc_exists() -> None:
    p = REPO_ROOT / "docs" / "why_llm_wiki.md"
    assert p.exists()
    text = p.read_text().lower()
    for needle in ("graphrag", "wiki", "relationships",
                   "contradict", "what do we currently believe"):
        assert needle in text, f"why_llm_wiki.md missing {needle!r}"


def test_method_comparison_doc_exists() -> None:
    p = REPO_ROOT / "docs" / "llm_wiki_vs_rag_vs_graphrag.md"
    assert p.exists()
    text = p.read_text()
    # Comparison table headers.
    for needle in ("Primary artifact", "Best at", "Weakness",
                   "Forensic example"):
        assert needle in text
    for method in ("Raw RAG", "GraphRAG-lite", "LLM Wiki", "Hybrid"):
        assert method in text


def test_readme_includes_why_not_just_graphrag_section() -> None:
    readme = (REPO_ROOT / "README.md").read_text()
    assert "Why not just GraphRAG?" in readme
    assert "compare-all" in readme


# --------------------------------------------------------------------------- #
# CLI help / subcommand wiring
# --------------------------------------------------------------------------- #


def test_cli_help_lists_phase5_commands() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "fw.py"), "--help"],
        capture_output=True, text=True, check=True,
    )
    help_text = result.stdout
    for cmd in ("graph-build", "graph-query", "graph-export",
                "compare-all", "benchmark-methods", "vector-query"):
        assert cmd in help_text, f"--help missing {cmd!r}"
