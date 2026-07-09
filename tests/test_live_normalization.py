"""Live-mode type normalization.

The live LLM occasionally returns entity/IOC types outside the schema's
vocabulary (observed in the first live smoke test: 'directory',
'suspicious_executable', 'reconnaissance_command'). These tests pin the
coercion behavior that keeps live ingest from crashing on them.
"""
from __future__ import annotations

from src.llm import normalize_llm_types
from src.schemas import ExtractedFacts


def _payload(entity_type: str, ioc_type: str) -> dict:
    return {
        "source_path": "raw_sources/case_x/file.txt",
        "entities": [{"type": entity_type, "value": "C:\\Tools"}],
        "iocs": [{
            "artifact": "DeskRest.exe",
            "type": ioc_type,
            "source": "raw_sources/case_x/file.txt",
            "reason": "unfamiliar binary",
        }],
    }


def test_unknown_types_coerce_to_other_and_are_noted() -> None:
    data = normalize_llm_types(_payload("directory", "suspicious_executable"))
    assert data["entities"][0]["type"] == "other"
    assert data["iocs"][0]["type"] == "other"
    notes = " ".join(data["notes"])
    assert "'directory'" in notes
    assert "'suspicious_executable'" in notes


def test_near_miss_types_map_to_canonical_spelling() -> None:
    data = normalize_llm_types(_payload("IP", "Registry Key"))
    assert data["entities"][0]["type"] == "ip"
    assert data["iocs"][0]["type"] == "registry_key"
    assert "notes" not in data  # canonical mappings are not noteworthy


def test_valid_types_pass_through_unchanged() -> None:
    data = normalize_llm_types(_payload("process", "hash"))
    assert data["entities"][0]["type"] == "process"
    assert data["iocs"][0]["type"] == "hash"
    assert "notes" not in data


def test_normalized_payload_validates() -> None:
    data = normalize_llm_types(_payload("reconnaissance_command", "directory"))
    facts = ExtractedFacts.model_validate(data)
    assert facts.entities[0].type == "other"
    assert facts.iocs[0].type == "other"


def test_missing_sections_are_tolerated() -> None:
    assert normalize_llm_types({"source_path": "x"}) == {"source_path": "x"}
