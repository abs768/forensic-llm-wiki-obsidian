"""Query operation must refuse to confirm malware on weak evidence and
must answer 'insufficient' rather than hallucinate when the wiki is empty."""
from __future__ import annotations

from pathlib import Path

from src.ingest import ingest_case
from src.query import INSUFFICIENT_SENTENCE, answer_question


def test_confirmed_malware_question_returns_no(project: Path) -> None:
    ingest_case(project, "case_001")
    ans = answer_question(project, "case_001", "Is this confirmed malware?")
    assert ans.insufficient is False
    assert ans.answer.lower().startswith("no")
    assert "confirmed" not in ans.answer.lower().split("not confirmed")[0]
    assert ans.classification == "hypothesis"
    assert ans.confidence in ("Low", "Medium")


def test_confirmed_malware_includes_contradicting_evidence(project: Path) -> None:
    ingest_case(project, "case_001")
    ans = answer_question(project, "case_001", "Is this confirmed malware?")
    blob = " ".join(ans.contradicting_evidence).lower()
    assert "defender" in blob or "0 threats" in blob or "scan" in blob


def test_persistence_question_returns_hypothesis(project: Path) -> None:
    ingest_case(project, "case_001")
    ans = answer_question(project, "case_001", "What evidence supports persistence?")
    assert ans.insufficient is False
    assert ans.classification == "hypothesis"
    assert any("hypotheses" in p for p in ans.supporting_pages)


def test_empty_wiki_says_insufficient(empty_project: Path) -> None:
    # No raw files, no state — query should refuse cleanly.
    ans = answer_question(empty_project, "case_001", "Is this confirmed malware?")
    assert ans.insufficient is True
    assert ans.answer == INSUFFICIENT_SENTENCE


def test_unrelated_question_returns_insufficient(project: Path) -> None:
    ingest_case(project, "case_001")
    ans = answer_question(
        project, "case_001",
        "What is the SHA-512 of the bootloader?",
    )
    assert ans.insufficient is True
    assert ans.answer == INSUFFICIENT_SENTENCE


def test_network_question_grounded_in_timeline(project: Path) -> None:
    ingest_case(project, "case_001")
    ans = answer_question(project, "case_001", "Are there any outbound network connections?")
    assert ans.insufficient is False
    assert any("198.51.100.42" in s or "network_connections" in s
               for s in ans.supporting_sources)
