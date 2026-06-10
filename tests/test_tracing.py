"""Trace logs and ingestion log are written and well-formed."""
from __future__ import annotations

import json
from pathlib import Path

from src.ingest import ingest_case
from src.tracing import ingestion_log_path, read_ingestion_log, read_traces, traces_path


def test_traces_file_created_during_ingest(project: Path) -> None:
    ingest_case(project, "case_001")
    p = traces_path(project, "case_001")
    assert p.exists()
    # One trace per processed file.
    lines = [ln for ln in p.read_text().splitlines() if ln.strip()]
    assert len(lines) == 6


def test_trace_record_has_required_fields(project: Path) -> None:
    ingest_case(project, "case_001")
    traces = read_traces(project, "case_001")
    assert traces
    t = traces[0]
    assert t.trace_id.startswith("trace_")
    assert t.operation == "ingest"
    assert t.case_id == "case_001"
    assert t.source_path is not None
    assert any(s.step == "hash_source" for s in t.steps)
    assert any(s.step == "extract_facts" for s in t.steps)
    for s in t.steps:
        assert s.status in {"ok", "error", "skipped"}
        assert s.duration_ms >= 0


def test_skipped_files_recorded_as_skipped_step(project: Path) -> None:
    ingest_case(project, "case_001")
    ingest_case(project, "case_001")  # second run, all should skip
    traces = read_traces(project, "case_001")
    # The second run added six more traces, all with a skip step.
    skip_traces = [t for t in traces if any(s.step == "skip" for s in t.steps)]
    assert len(skip_traces) >= 6


def test_ingestion_log_written(project: Path) -> None:
    ingest_case(project, "case_001")
    p = ingestion_log_path(project, "case_001")
    assert p.exists()
    entries = read_ingestion_log(project, "case_001")
    assert len(entries) == 1
    entry = entries[0]
    assert entry.case_id == "case_001"
    assert len(entry.sources_processed) == 6
    assert entry.dry_run is False
    assert entry.mode == "mock"


def test_dry_run_does_not_write_traces(project: Path) -> None:
    ingest_case(project, "case_001", dry_run=True)
    p = traces_path(project, "case_001")
    assert not p.exists()
    p2 = ingestion_log_path(project, "case_001")
    assert not p2.exists()
