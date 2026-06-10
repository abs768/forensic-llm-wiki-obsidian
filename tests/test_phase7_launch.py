"""Phase 7: launch-readiness artifacts.

Tolerant existence + concept-mention checks. No brittle wording assertions.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.ingest import ingest_case

REPO_ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------- #
# Launch docs
# --------------------------------------------------------------------------- #


def test_threats_to_validity_exists_and_is_honest() -> None:
    p = REPO_ROOT / "docs" / "threats_to_validity.md"
    assert p.exists()
    text = p.read_text().lower()
    # The document must concede the obvious limits.
    for needle in ("synthetic", "bm25", "graphrag-lite",
                   "mock", "not a malware verdict"):
        assert needle in text, f"threats_to_validity missing {needle!r}"


def test_case_study_exists_with_required_sections() -> None:
    p = REPO_ROOT / "CASE_STUDY.md"
    assert p.exists()
    text = p.read_text()
    for header in ("## Problem",
                   "## Why raw RAG is insufficient",
                   "## Why GraphRAG alone is not enough",
                   "## Architecture",
                   "## Case evolution benchmark",
                   "## Adversarial overclaim test",
                   "## AI engineering decisions",
                   "## Software engineering decisions",
                   "## What was hard",
                   "## Limitations",
                   "## Future work"):
        assert header in text, f"CASE_STUDY missing section {header!r}"
    # The core insight quote must be present.
    assert "citation discipline" in text.lower()
    assert "facts from hypotheses" in text.lower()


def test_live_llm_smoke_test_doc_exists() -> None:
    p = REPO_ROOT / "examples" / "live_llm_smoke_test.md"
    assert p.exists()
    text = p.read_text()
    assert "ANTHROPIC_API_KEY" in text
    assert "FORENSIC_WIKI_LLM" in text
    # Must include an "Example recorded run" template, not fake numbers.
    assert "Example recorded run" in text
    assert "Template for maintainers" in text


def test_interview_talking_points_exist() -> None:
    p = REPO_ROOT / "docs" / "interview_talking_points.md"
    assert p.exists()
    text = p.read_text().lower()
    # Must mention every required Q section by intent. We do a tolerant
    # substring check so minor wording changes (e.g. "Why not just GraphRAG?"
    # vs "Why not GraphRAG?") don't break the test.
    for needle in ("what problem does this solve",
                   "why not traditional rag",
                   "what is the architecture",
                   "what was hardest",
                   "how do you prevent hallucinations",
                   "how does human review work"):
        assert needle in text, f"talking points missing {needle!r}"
    # The GraphRAG positioning question is allowed either spelling.
    assert "why not graphrag" in text or "why not just graphrag" in text


def test_launch_checklist_exists() -> None:
    p = REPO_ROOT / "docs" / "launch_checklist.md"
    assert p.exists()
    text = p.read_text()
    assert "launch-check" in text


def test_demo_video_script_exists() -> None:
    p = REPO_ROOT / "docs" / "demo_video_script.md"
    assert p.exists()
    text = p.read_text().lower()
    assert "evolve" in text
    assert "compare-all" in text
    assert "benchmark-methods" in text or "benchmark methods" in text


# --------------------------------------------------------------------------- #
# Adversarial overclaim case
# --------------------------------------------------------------------------- #


def test_adversarial_case_raw_sources_exist() -> None:
    rs = REPO_ROOT / "raw_sources" / "case_003_adversarial_overclaim"
    assert rs.is_dir()
    for name in ("powershell_history.txt", "registry_run_keys.reg",
                 "network_connections.csv", "defender_scan.txt",
                 "hash_reputation.txt", "investigator_notes.md"):
        assert (rs / name).exists(), f"adversarial missing {name}"


def test_adversarial_investigator_note_actually_overclaims() -> None:
    notes = (REPO_ROOT / "raw_sources" / "case_003_adversarial_overclaim"
             / "investigator_notes.md").read_text().lower()
    # The whole point of the case is the analyst's three explicit overclaims.
    assert "confirmed malware" in notes
    assert "exfiltrated" in notes or "exfil" in notes
    assert "stole" in notes


def test_adversarial_eval_exists_with_enough_questions() -> None:
    p = REPO_ROOT / "evals" / "case_003_adversarial_overclaim_eval.json"
    assert p.exists()
    payload = json.loads(p.read_text())
    items = payload.get("items", payload)
    assert len(items) >= 10


def test_wiki_refuses_adversarial_confirmed_malware(project: Path) -> None:
    """The wiki must not endorse the analyst's confirmed-malware claim."""
    from src.query import answer_question
    ingest_case(project, "case_003_adversarial_overclaim")
    ans = answer_question(project, "case_003_adversarial_overclaim",
                          "Is this confirmed malware?")
    assert ans.insufficient is False
    assert ans.answer.lower().startswith("no")


def test_wiki_refuses_adversarial_exfiltration(project: Path) -> None:
    """The wiki must not endorse the analyst's exfiltration overclaim."""
    from src.query import answer_question, format_answer
    ingest_case(project, "case_003_adversarial_overclaim")
    ans = answer_question(project, "case_003_adversarial_overclaim",
                          "Did exfiltration occur?")
    text = format_answer(ans).lower()
    assert "not confirmed" in text
    # And the wiki's own answer must not echo the analyst's overclaim verbatim.
    assert "exfiltration occurred" not in text
    assert "data was stolen" not in text


# --------------------------------------------------------------------------- #
# README + PROJECT_SUMMARY tighten
# --------------------------------------------------------------------------- #


def test_readme_includes_thesis_lines() -> None:
    readme = (REPO_ROOT / "README.md").read_text()
    for needle in ("RAG retrieves",
                   "GraphRAG relates",
                   "LLM Wiki maintains",
                   "Hybrid combines"):
        assert needle in readme, f"README missing thesis line {needle!r}"


def test_readme_links_threats_to_validity() -> None:
    readme = (REPO_ROOT / "README.md").read_text()
    assert "threats_to_validity" in readme or "Threats to Validity" in readme


def test_readme_includes_method_comparison_table() -> None:
    readme = (REPO_ROOT / "README.md").read_text()
    # Method-comparison table column headers.
    assert "Best at" in readme
    assert "Weak at" in readme


def test_project_summary_has_resume_bullet() -> None:
    text = (REPO_ROOT / "PROJECT_SUMMARY.md").read_text()
    assert "Resume bullet" in text or "resume bullet" in text
    # Resume bullet must mention every elevator-pitch phrase.
    lower = text.lower()
    for needle in ("forensic llm wiki",
                   "obsidian",
                   "rag",
                   "graphrag",
                   "hybrid"):
        assert needle in lower, f"resume bullet missing concept {needle!r}"


# --------------------------------------------------------------------------- #
# Assets folder
# --------------------------------------------------------------------------- #


def test_assets_folder_exists_with_required_files() -> None:
    a = REPO_ROOT / "assets"
    assert a.is_dir()
    for name in ("architecture.mmd", "rag_vs_llm_wiki.mmd",
                 "method_comparison_table.md", "demo_flow.md"):
        assert (a / name).exists(), f"assets/{name} missing"


def test_architecture_mmd_describes_flow() -> None:
    text = (REPO_ROOT / "assets" / "architecture.mmd").read_text().lower()
    # Show the ingest pipeline going from raw + schema to wiki + indexes.
    assert "raw sources" in text
    assert "schema" in text
    assert "wiki" in text


def test_rag_vs_wiki_mmd_describes_both_flows() -> None:
    text = (REPO_ROOT / "assets" / "rag_vs_llm_wiki.mmd").read_text().lower()
    assert "rag" in text or "retrieve" in text
    assert "wiki" in text
    assert "contradiction" in text or "hypothes" in text


# --------------------------------------------------------------------------- #
# Makefile
# --------------------------------------------------------------------------- #


def test_makefile_has_launch_check_target() -> None:
    text = (REPO_ROOT / "Makefile").read_text()
    assert "launch-check:" in text


def test_makefile_has_adversarial_target() -> None:
    text = (REPO_ROOT / "Makefile").read_text()
    assert "adversarial:" in text


# --------------------------------------------------------------------------- #
# Benchmark report artifacts
# --------------------------------------------------------------------------- #


def test_committed_benchmark_results_exist() -> None:
    for name in ("results.md", "evolution_report.md", "method_comparison.md"):
        p = REPO_ROOT / "benchmark_results" / "case_002_evolving" / name
        assert p.exists(), f"missing benchmark artifact {name}"


def test_committed_adversarial_results_exist() -> None:
    p = REPO_ROOT / "benchmark_results" / "case_003_adversarial_overclaim" / "results.md"
    assert p.exists()


# --------------------------------------------------------------------------- #
# (deliberately tolerant) docs index linkage
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("doc", [
    "architecture.md",
    "rag_vs_llm_wiki.md",
    "why_llm_wiki.md",
    "llm_wiki_vs_rag_vs_graphrag.md",
    "mcp_setup.md",
    "obsidian_workflow.md",
    "human_review.md",
    "threats_to_validity.md",
    "interview_talking_points.md",
    "demo_video_script.md",
    "launch_checklist.md",
])
def test_readme_links_to_each_phase7_doc(doc: str) -> None:
    readme = (REPO_ROOT / "README.md").read_text()
    assert doc in readme, f"README should link to docs/{doc}"
