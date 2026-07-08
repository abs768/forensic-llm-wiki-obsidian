"""Lightweight structured tracing.

Two append-only logs live under ``.fw/``:

  traces.jsonl         — one record per operation (ingest, query, lint, ...)
  ingestion_log.jsonl  — one record per ingest run, with file lists and mode

Each line is a complete JSON object. This is intentionally low-tech — no
Langfuse, no OpenTelemetry. The point is that every run leaves an audit
trail you can grep, diff, and reason about.
"""
from __future__ import annotations

import json
import secrets
import time
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Literal

from .schemas import IngestionLogEntry, TraceRecord, TraceStep
from .wiki_io import fw_dir


def traces_path(project_root: Path, case_id: str) -> Path:
    return fw_dir(project_root, case_id) / "traces.jsonl"


def ingestion_log_path(project_root: Path, case_id: str) -> Path:
    return fw_dir(project_root, case_id) / "ingestion_log.jsonl"


# --------------------------------------------------------------------------- #
# Tracer — used as a context manager to record an operation
# --------------------------------------------------------------------------- #


class Tracer:
    """Records an operation as a TraceRecord, written on close.

    Usage:

        with Tracer(project_root, case_id, "ingest", source_path=...) as t:
            with t.step("hash_source"):
                ...
            with t.step("extract_entities"):
                ...
    """

    def __init__(
        self,
        project_root: Path,
        case_id: str,
        operation: str,
        *,
        source_path: str | None = None,
        enabled: bool = True,
    ) -> None:
        self.project_root = project_root
        self.enabled = enabled
        self.record = TraceRecord(
            trace_id=_new_trace_id(),
            operation=operation,
            case_id=case_id,
            source_path=source_path,
        )

    def step(self, name: str) -> _StepContext:
        return _StepContext(self, name)

    def add_step(self, step: TraceStep) -> None:
        self.record.steps.append(step)

    def __enter__(self) -> Tracer:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if not self.enabled:
            return
        fw_dir(self.project_root, self.record.case_id).mkdir(parents=True, exist_ok=True)
        path = traces_path(self.project_root, self.record.case_id)
        with path.open("a", encoding="utf-8") as f:
            f.write(self.record.model_dump_json() + "\n")


class _StepContext:
    def __init__(self, tracer: Tracer, name: str) -> None:
        self.tracer = tracer
        self.name = name
        self.t0 = 0.0
        self.status = "ok"
        self.detail: str | None = None

    def __enter__(self) -> _StepContext:
        self.t0 = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> Literal[False]:
        dt = int((time.perf_counter() - self.t0) * 1000)
        if exc is not None:
            self.status = "error"
            self.detail = f"{exc.__class__.__name__}: {exc}"
        self.tracer.add_step(TraceStep(
            step=self.name,
            status=self.status,  # type: ignore[arg-type]
            duration_ms=dt,
            detail=self.detail,
        ))
        # Propagate exceptions.
        return False

    def mark_skipped(self, detail: str = "") -> None:
        self.status = "skipped"
        if detail:
            self.detail = detail


# --------------------------------------------------------------------------- #
# Ingestion log helpers
# --------------------------------------------------------------------------- #


def append_ingestion_log(project_root: Path, entry: IngestionLogEntry) -> None:
    fw_dir(project_root, entry.case_id).mkdir(parents=True, exist_ok=True)
    path = ingestion_log_path(project_root, entry.case_id)
    with path.open("a", encoding="utf-8") as f:
        f.write(entry.model_dump_json() + "\n")


def read_traces(project_root: Path, case_id: str) -> list[TraceRecord]:
    path = traces_path(project_root, case_id)
    if not path.exists():
        return []
    out: list[TraceRecord] = []
    for line in path.read_text().splitlines():
        if line.strip():
            out.append(TraceRecord.model_validate(json.loads(line)))
    return out


def read_ingestion_log(project_root: Path, case_id: str) -> list[IngestionLogEntry]:
    path = ingestion_log_path(project_root, case_id)
    if not path.exists():
        return []
    out: list[IngestionLogEntry] = []
    for line in path.read_text().splitlines():
        if line.strip():
            out.append(IngestionLogEntry.model_validate(json.loads(line)))
    return out


def _new_trace_id() -> str:
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    return f"trace_{ts}_{secrets.token_hex(4)}"
