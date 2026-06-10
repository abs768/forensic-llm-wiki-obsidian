"""Naive RAG baseline and side-by-side compare."""
from __future__ import annotations

from pathlib import Path

from src.compare import compare, format_comparison
from src.ingest import ingest_case
from src.rag import lexical_search, rag_query


def test_lexical_search_finds_registry_file(project: Path) -> None:
    matches = lexical_search(project, "case_001", "DeskRest registry persistence")
    assert matches
    top = matches[0]
    assert "registry_run_keys.reg" in top.source_path or "powershell_history" in top.source_path


def test_rag_query_returns_raw_snippets(project: Path) -> None:
    ans = rag_query(project, "case_001", "Is this confirmed malware?")
    assert ans.fell_back_to_raw_sources is True
    assert ans.supporting_sources
    blob = " ".join(ans.evidence_items).lower()
    # The naive baseline pulls both sides of the conflict without reconciling.
    assert "malware" in blob or "defender" in blob


def test_rag_query_lacks_synthesis_signals(project: Path) -> None:
    ans = rag_query(project, "case_001", "Is this confirmed malware?")
    # No hypotheses, no contradictions ledger in the naive baseline.
    assert ans.supporting_pages == []
    assert ans.contradicting_evidence == []


def test_compare_produces_both_answers(project: Path) -> None:
    ingest_case(project, "case_001")
    c = compare(project, "case_001", "Is this confirmed malware?")
    assert c.wiki.fell_back_to_raw_sources is False
    assert c.rag.fell_back_to_raw_sources is True
    out = format_comparison(c)
    assert "Forensic LLM Wiki" in out
    assert "Naive raw-source RAG baseline" in out


def test_compare_wiki_answer_is_richer(project: Path) -> None:
    ingest_case(project, "case_001")
    c = compare(project, "case_001", "Is this confirmed malware?")
    assert c.wiki.evidence_items, "wiki answer must list claim/event evidence"
    assert c.wiki.contradicting_evidence, "wiki must surface the AV vs activity contradiction"
