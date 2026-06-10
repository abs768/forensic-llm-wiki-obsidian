"""Manifest behaviour: skip unchanged, reprocess changed, force, status fields."""
from __future__ import annotations

from pathlib import Path

from src.ingest import ingest_case
from src.manifest import load_manifest, manifest_path
from src.wiki_io import raw_case_dir


def test_manifest_created_on_first_ingest(project: Path) -> None:
    ingest_case(project, "case_001")
    p = manifest_path(project, "case_001")
    assert p.exists()
    manifest = load_manifest(project, "case_001")
    assert manifest.case_id == "case_001"
    assert manifest.schema_version == "v1"
    assert len(manifest.sources) == 6
    assert manifest.last_ingest_at is not None


def test_manifest_records_pages_touched(project: Path) -> None:
    ingest_case(project, "case_001")
    manifest = load_manifest(project, "case_001")
    entry = next(e for e in manifest.sources
                 if e.source_path.endswith("registry_run_keys.reg"))
    assert "hypotheses.md" in entry.pages_touched
    assert "iocs.md" in entry.pages_touched


def test_unchanged_source_is_skipped_on_reingest(project: Path) -> None:
    ingest_case(project, "case_001")
    second = ingest_case(project, "case_001")
    assert not second.sources_processed
    assert len(second.sources_skipped) == 6


def test_changed_source_is_reprocessed(project: Path) -> None:
    ingest_case(project, "case_001")
    notes = raw_case_dir(project, "case_001") / "investigator_notes.md"
    notes.write_text(notes.read_text() + "\n- new clue: outbound to 198.51.100.42\n")
    second = ingest_case(project, "case_001")
    assert any("investigator_notes" in s for s in second.sources_processed)
    assert len(second.sources_skipped) == 5


def test_force_flag_reprocesses_everything(project: Path) -> None:
    ingest_case(project, "case_001")
    second = ingest_case(project, "case_001", force=True)
    assert len(second.sources_processed) == 6
    assert not second.sources_skipped


def test_changed_only_is_equivalent_to_default(project: Path) -> None:
    ingest_case(project, "case_001")
    second = ingest_case(project, "case_001", changed_only=True)
    assert not second.sources_processed


def test_manifest_status_is_processed(project: Path) -> None:
    ingest_case(project, "case_001")
    manifest = load_manifest(project, "case_001")
    for entry in manifest.sources:
        assert entry.status == "processed"
        assert entry.sha256 and len(entry.sha256) == 64
