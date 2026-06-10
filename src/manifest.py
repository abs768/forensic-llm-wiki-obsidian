"""Source manifest.

Tracks which raw source files have been ingested, their sha256, when they
were last processed, and which wiki pages each ingest touched. Stored at
``wiki/cases/<case_id>/.fw/manifest.json``.

The manifest is the source of truth for "what is new or changed since last
ingest". The wiki state file (``.fw/state.json``) holds the compiled
knowledge; the manifest holds the bookkeeping.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .schemas import Manifest, ManifestEntry
from .wiki_io import fw_dir


def manifest_path(project_root: Path, case_id: str) -> Path:
    return fw_dir(project_root, case_id) / "manifest.json"


def load_manifest(project_root: Path, case_id: str) -> Manifest:
    p = manifest_path(project_root, case_id)
    if not p.exists():
        return Manifest(case_id=case_id)
    return Manifest.model_validate_json(p.read_text())


def save_manifest(project_root: Path, manifest: Manifest) -> None:
    p = manifest_path(project_root, manifest.case_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(manifest.model_dump_json(indent=2))


def needs_processing(manifest: Manifest, source_path: str, sha: str) -> bool:
    for entry in manifest.sources:
        if entry.source_path == source_path:
            return entry.sha256 != sha or entry.status != "processed"
    return True


def record_processed(
    manifest: Manifest,
    source_path: str,
    sha: str,
    pages_touched: list[str],
    *,
    status: str = "processed",
) -> ManifestEntry:
    entry = ManifestEntry(
        source_path=source_path,
        sha256=sha,
        last_ingested_at=_now(),
        status=status,
        pages_touched=sorted(set(pages_touched)),
    )
    manifest.upsert(entry)
    return entry


def mark_ingest_run(manifest: Manifest) -> None:
    manifest.last_ingest_at = _now()


def mark_lint_run(manifest: Manifest) -> None:
    manifest.last_full_lint_at = _now()


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"
