"""Round-trip the state file and confirm rendered markdown matches the
in-memory snapshot."""
from __future__ import annotations

from pathlib import Path

from src.schemas import IOC, Citation, Entity, Event, Hypothesis
from src.wiki_io import (
    WikiState,
    case_dir,
    load_state,
    render_all_pages,
    save_state,
)


def _sample_state() -> WikiState:
    state = WikiState(case_id="case_test")
    e = Entity(
        type="file",
        value="totally_fine.exe",
        appears_in=["raw_sources/case_test/notes.md"],
        citations=[Citation(kind="source", target="raw_sources/case_test/notes.md")],
    )
    state.entities[e.key] = e
    state.events.append(Event(
        timestamp="2025-12-01 08:00:00",
        description="user logged in",
        citation=Citation(kind="source", target="raw_sources/case_test/notes.md"),
    ))
    state.iocs["file:totally_fine.exe"] = IOC(
        artifact="totally_fine.exe",
        type="file",
        first_seen="2025-12-01 08:00:00",
        source="raw_sources/case_test/notes.md",
        confidence="Low",
        reason="placeholder",
        related=["[[entities]]"],
    )
    state.hypotheses["benign"] = Hypothesis(
        title="Possibly Benign Behaviour",
        confidence="Low",
        facts=["Source: raw_sources/case_test/notes.md — login event"],
        inference="Login alone is not suspicious.",
        supporting_evidence=["Source: raw_sources/case_test/notes.md"],
    )
    state.source_files["raw_sources/case_test/notes.md"] = "deadbeef"
    return state


def test_state_round_trip(tmp_path: Path) -> None:
    (tmp_path / "raw_sources" / "case_test").mkdir(parents=True)
    state = _sample_state()
    save_state(tmp_path, state)
    reloaded = load_state(tmp_path, "case_test")
    assert reloaded.case_id == "case_test"
    assert "file:totally_fine.exe" in reloaded.entities
    assert reloaded.events[0].description == "user logged in"


def test_render_writes_all_pages(tmp_path: Path) -> None:
    state = _sample_state()
    render_all_pages(tmp_path, state)
    cdir = case_dir(tmp_path, "case_test")
    expected = {"index.md", "timeline.md", "entities.md", "iocs.md",
                "hypotheses.md", "contradictions.md", "open_questions.md",
                "final_report.md"}
    assert {p.name for p in cdir.iterdir() if p.suffix == ".md"} >= expected


def test_rendered_entities_page_contains_entity_value(tmp_path: Path) -> None:
    state = _sample_state()
    render_all_pages(tmp_path, state)
    entities = (case_dir(tmp_path, "case_test") / "entities.md").read_text()
    assert "totally_fine.exe" in entities
    assert "Source: raw_sources/case_test/notes.md" in entities


def test_rendered_timeline_is_chronological(tmp_path: Path) -> None:
    state = _sample_state()
    state.events.append(Event(
        timestamp="2025-12-01 07:00:00",
        description="earlier event",
        citation=Citation(kind="source", target="raw_sources/case_test/notes.md"),
    ))
    state.events.append(Event(
        timestamp="unknown",
        description="undated event",
        citation=Citation(kind="source", target="raw_sources/case_test/notes.md"),
    ))
    render_all_pages(tmp_path, state)
    timeline = (case_dir(tmp_path, "case_test") / "timeline.md").read_text()
    earlier = timeline.index("earlier event")
    later = timeline.index("user logged in")
    undated = timeline.index("undated event")
    assert earlier < later < undated
