"""Phase 2 query: wiki first, then raw-source fallback when wiki is empty."""
from __future__ import annotations

from pathlib import Path

from src.ingest import ingest_case
from src.query import INSUFFICIENT_SENTENCE, answer_question, format_answer


def test_query_uses_wiki_before_raw_sources(project: Path) -> None:
    ingest_case(project, "case_001")
    ans = answer_question(project, "case_001", "Is this confirmed malware?")
    assert ans.fell_back_to_raw_sources is False
    text = format_answer(ans)
    assert "Answer:" in text
    assert "Assessment:" in text
    assert "Evidence:" in text
    assert "Confidence:" in text
    assert "Sources:" in text


def test_query_format_includes_claim_ids(project: Path) -> None:
    ingest_case(project, "case_001")
    ans = answer_question(project, "case_001", "Is this confirmed malware?")
    text = format_answer(ans)
    assert "claim_" in text


def test_query_falls_back_to_raw_when_wiki_empty(project: Path) -> None:
    # No ingest — wiki has no compiled view yet.
    ans = answer_question(project, "case_001", "Tell me about DeskRest")
    assert ans.fell_back_to_raw_sources is True
    text = format_answer(ans)
    assert "fell back to raw-source search" in text.lower()


def test_query_fallback_cites_raw_sources(project: Path) -> None:
    ans = answer_question(project, "case_001", "registry run keys")
    assert ans.fell_back_to_raw_sources is True
    assert any("registry_run_keys.reg" in s for s in ans.supporting_sources)


def test_query_returns_insufficient_when_nothing_matches(empty_project: Path) -> None:
    ans = answer_question(empty_project, "case_001",
                          "What is the SHA-512 of the bootloader?")
    assert ans.insufficient is True
    assert ans.answer == INSUFFICIENT_SENTENCE
