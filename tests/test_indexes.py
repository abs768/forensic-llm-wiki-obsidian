"""Structured index files (.fw/events.json, entities.json, claims.json)."""
from __future__ import annotations

import json
from pathlib import Path

from src.index import claims_path, entities_path, events_path
from src.ingest import ingest_case


def test_events_json_created(project: Path) -> None:
    ingest_case(project, "case_001")
    p = events_path(project, "case_001")
    assert p.exists()
    data = json.loads(p.read_text())
    assert data, "events.json must not be empty"
    for ev in data:
        assert ev["event_id"].startswith("evt_")
        assert ev["source_path"].startswith("raw_sources/")
        assert ev["event_type"] in {
            "process_execution", "network_connection", "registry_change",
            "av_scan", "investigator_note", "other",
        }


def test_entities_json_created(project: Path) -> None:
    ingest_case(project, "case_001")
    p = entities_path(project, "case_001")
    data = json.loads(p.read_text())
    assert data
    for e in data:
        assert e["entity_id"].startswith("ent_")
        assert e["value"]
        assert "entities.md" in e["related_pages"]


def test_claims_json_records_hypotheses(project: Path) -> None:
    ingest_case(project, "case_001")
    p = claims_path(project, "case_001")
    data = json.loads(p.read_text())
    assert data
    persistence = next(
        (c for c in data if "persistence" in c["claim_text"].lower()), None
    )
    assert persistence is not None
    assert persistence["claim_id"].startswith("claim_")
    assert persistence["claim_type"] == "hypothesis"
    assert persistence["supporting_evidence"]
    # contradicting evidence: clean Defender scan
    assert any("defender" in e["evidence_text"].lower()
               for e in persistence["contradicting_evidence"])


def test_ids_are_stable_across_reingest(project: Path) -> None:
    ingest_case(project, "case_001")
    first = json.loads(claims_path(project, "case_001").read_text())
    ingest_case(project, "case_001", force=True)
    second = json.loads(claims_path(project, "case_001").read_text())
    # Every claim that survived must keep its claim_id.
    first_by_text = {c["claim_text"]: c["claim_id"] for c in first}
    for c in second:
        if c["claim_text"] in first_by_text:
            assert c["claim_id"] == first_by_text[c["claim_text"]]


def test_citation_ids_appear_in_markdown(project: Path) -> None:
    ingest_case(project, "case_001")
    hyps = (project / "wiki" / "cases" / "case_001" / "hypotheses.md").read_text()
    assert "claim_" in hyps
    entities = (project / "wiki" / "cases" / "case_001" / "entities.md").read_text()
    assert "ent_" in entities
    timeline = (project / "wiki" / "cases" / "case_001" / "timeline.md").read_text()
    assert "evt_" in timeline
