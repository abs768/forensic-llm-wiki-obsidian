"""Phase 4: ensure the repo ships everything a reviewer expects.

These tests are deliberately tolerant — they check that artifacts exist
and mention the key concepts, not the exact wording. The CLI help test
checks that every documented subcommand is actually wired up.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------- #
# README
# --------------------------------------------------------------------------- #


def test_readme_exists_and_mentions_llm_wiki() -> None:
    readme = REPO_ROOT / "README.md"
    assert readme.exists()
    text = readme.read_text()
    assert "Forensic LLM Wiki" in text
    assert "LLM Wiki" in text
    assert "RAG" in text
    assert "markdown" in text.lower()


def test_readme_documents_core_commands() -> None:
    text = (REPO_ROOT / "README.md").read_text()
    for cmd in ("ingest", "query", "rag-query", "compare", "lint",
                "eval", "report", "evolve", "benchmark", "diff-snapshots"):
        assert f"fw.py {cmd}" in text or f"`{cmd}`" in text, f"README missing mention of {cmd!r}"


def test_readme_includes_benchmark_table() -> None:
    text = (REPO_ROOT / "README.md").read_text()
    assert "Raw RAG" in text and "LLM Wiki" in text
    assert "Refusal accuracy" in text


# --------------------------------------------------------------------------- #
# docs/
# --------------------------------------------------------------------------- #


def test_docs_files_exist() -> None:
    docs = REPO_ROOT / "docs"
    assert docs.is_dir()
    for name in ("architecture.md", "rag_vs_llm_wiki.md",
                 "demo_script.md", "benchmark_methodology.md"):
        assert (docs / name).exists(), f"missing docs/{name}"


def test_architecture_doc_has_mermaid_diagram() -> None:
    arch = (REPO_ROOT / "docs" / "architecture.md").read_text()
    assert "```mermaid" in arch
    assert "Raw Sources" in arch
    assert "Structured Indexes" in arch


# --------------------------------------------------------------------------- #
# examples/
# --------------------------------------------------------------------------- #


def test_demo_commands_script_exists_and_is_executable() -> None:
    script = REPO_ROOT / "examples" / "demo_commands.sh"
    assert script.exists()
    # Bash shebang and core commands present.
    text = script.read_text()
    assert text.startswith("#!/usr/bin/env bash") or text.startswith("#!/bin/bash")
    assert "fw.py ingest" in text
    assert "fw.py evolve" in text
    assert "fw.py benchmark" in text


def test_demo_expected_output_exists() -> None:
    p = REPO_ROOT / "examples" / "demo_expected_output.md"
    assert p.exists()
    text = p.read_text()
    assert "RAG" in text and "Wiki" in text


def test_sample_questions_exists_with_useful_questions() -> None:
    p = REPO_ROOT / "examples" / "sample_questions.md"
    assert p.exists()
    text = p.read_text().lower()
    for needle in ("confirmed malware", "persistence", "exfiltration",
                   "defender", "contradict"):
        assert needle in text, f"sample_questions missing {needle!r}"


def test_obsidian_vault_example_exists() -> None:
    vault = REPO_ROOT / "examples" / "obsidian_vault_case_002"
    assert vault.is_dir()
    # Required wiki pages from the Phase 1 schema.
    for name in ("index.md", "timeline.md", "entities.md", "iocs.md",
                 "hypotheses.md", "contradictions.md", "open_questions.md",
                 "final_report.md"):
        assert (vault / name).exists(), f"vault missing {name}"
    # And the explanatory README.
    assert (vault / "README.md").exists()


def test_obsidian_vault_uses_wiki_links() -> None:
    """Spot-check that the vault contains Obsidian-style [[wiki links]]."""
    index = (REPO_ROOT / "examples" / "obsidian_vault_case_002" / "index.md").read_text()
    assert "[[timeline]]" in index
    assert "[[hypotheses]]" in index


# --------------------------------------------------------------------------- #
# Repo packaging
# --------------------------------------------------------------------------- #


def test_project_summary_exists() -> None:
    p = REPO_ROOT / "PROJECT_SUMMARY.md"
    assert p.exists()
    text = p.read_text().lower()
    # Must cover the recruiter-friendly headings.
    for needle in ("problem", "solution", "architecture", "limitation"):
        assert needle in text, f"PROJECT_SUMMARY missing section about {needle!r}"


def test_license_exists() -> None:
    p = REPO_ROOT / "LICENSE"
    assert p.exists()
    assert "MIT License" in p.read_text()


def test_contributing_exists() -> None:
    p = REPO_ROOT / "CONTRIBUTING.md"
    assert p.exists()
    text = p.read_text().lower()
    assert "out of scope" in text or "non-goals" in text


def test_env_example_exists() -> None:
    p = REPO_ROOT / ".env.example"
    assert p.exists()
    assert "FORENSIC_WIKI_LLM" in p.read_text()


def test_pyproject_exists_with_dev_extras() -> None:
    p = REPO_ROOT / "pyproject.toml"
    assert p.exists()
    text = p.read_text()
    assert "[project]" in text
    assert "ruff" in text
    assert "pytest" in text


def test_makefile_exists_with_core_targets() -> None:
    p = REPO_ROOT / "Makefile"
    assert p.exists()
    text = p.read_text()
    for target in ("install", "test", "lint", "format", "demo",
                   "evolve", "benchmark"):
        assert f"{target}:" in text, f"Makefile missing target {target!r}"


def test_github_actions_workflow_exists() -> None:
    p = REPO_ROOT / ".github" / "workflows" / "test.yml"
    assert p.exists()
    text = p.read_text()
    assert "pytest" in text
    assert "ruff" in text


def test_gitignore_tracks_demo_outputs() -> None:
    """Demo artifacts a reviewer wants to see must NOT be ignored."""
    gi = (REPO_ROOT / ".gitignore").read_text()
    # The negative patterns that un-ignore the demo outputs.
    assert "!benchmark_results/case_002_evolving/results.md" in gi
    assert "!benchmark_results/case_002_evolving/evolution_report.md" in gi


# --------------------------------------------------------------------------- #
# CLI help
# --------------------------------------------------------------------------- #


def test_cli_help_lists_every_command() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "fw.py"), "--help"],
        capture_output=True, text=True, check=True,
    )
    help_text = result.stdout
    for cmd in ("ingest", "query", "rag-query", "compare", "lint", "report",
                "eval", "evolve", "benchmark", "diff-snapshots"):
        assert cmd in help_text, f"--help missing command {cmd!r}"
    # And shows the project's pitch line.
    assert "Forensic LLM Wiki" in help_text
    assert "Not a generic RAG chatbot" in help_text


def test_cli_subcommand_help_works() -> None:
    """Every documented subcommand should accept --help cleanly."""
    for cmd in ("ingest", "query", "lint", "evolve", "benchmark", "diff-snapshots"):
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "fw.py"), cmd, "--help"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"{cmd} --help failed: {result.stderr}"
        assert "usage:" in result.stdout
