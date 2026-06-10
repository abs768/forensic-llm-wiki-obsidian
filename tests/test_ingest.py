"""End-to-end ingest behaviour, including the requirement that one raw
source touches multiple wiki pages and that raw sources stay immutable."""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest

from src.ingest import ingest_case
from src.wiki_io import case_dir, load_state, raw_case_dir


def _hash_dir(d: Path) -> dict[str, str]:
    out = {}
    for p in sorted(d.iterdir()):
        out[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def test_ingest_demo_case_processes_all_files(project: Path) -> None:
    report = ingest_case(project, "case_001")
    assert len(report.sources_processed) == 6
    assert not report.sources_skipped


def test_ingest_preserves_raw_sources_unchanged(project: Path) -> None:
    raw = raw_case_dir(project, "case_001")
    before = _hash_dir(raw)
    ingest_case(project, "case_001")
    after = _hash_dir(raw)
    assert before == after, "raw_sources must never be modified by ingest"


def test_single_registry_source_updates_multiple_pages(tmp_path: Path) -> None:
    """The key 'compounding' claim: one source touches many pages."""
    raw = tmp_path / "raw_sources" / "case_solo"
    raw.mkdir(parents=True)
    (tmp_path / "wiki").mkdir()
    (raw / "registry_run_keys.reg").write_text(
        'Windows Registry Editor Version 5.00\n\n'
        '[HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run]\n'
        '"BadGuy"="\\"C:\\\\Tools\\\\bad.exe\\""\n'
    )
    ingest_case(tmp_path, "case_solo")

    cdir = case_dir(tmp_path, "case_solo")
    timeline = (cdir / "timeline.md").read_text()
    entities = (cdir / "entities.md").read_text()
    iocs = (cdir / "iocs.md").read_text()
    hyps = (cdir / "hypotheses.md").read_text()

    assert "bad.exe" in entities.lower()
    assert "bad.exe" in iocs.lower()
    assert "registry value" in timeline.lower()
    assert "persistence" in hyps.lower()


def test_re_ingest_skips_unchanged_files(project: Path) -> None:
    first = ingest_case(project, "case_001")
    second = ingest_case(project, "case_001")
    assert first.sources_processed and not first.sources_skipped
    assert not second.sources_processed
    assert len(second.sources_skipped) == len(first.sources_processed)


def test_re_ingest_with_force_reprocesses(project: Path) -> None:
    ingest_case(project, "case_001")
    second = ingest_case(project, "case_001", force=True)
    assert second.sources_processed and not second.sources_skipped


def test_changed_file_is_re_extracted(project: Path) -> None:
    ingest_case(project, "case_001")
    notes = raw_case_dir(project, "case_001") / "investigator_notes.md"
    notes.write_text(notes.read_text() + "\n- Update: new lead found in event 4625.\n")
    report = ingest_case(project, "case_001")
    assert any("investigator_notes" in p for p in report.sources_processed)


def test_missing_case_raises(empty_project: Path) -> None:
    shutil.rmtree(empty_project / "raw_sources" / "case_001")
    with pytest.raises(FileNotFoundError):
        ingest_case(empty_project, "case_001")


def test_contradiction_detected_between_persistence_and_clean_av(project: Path) -> None:
    ingest_case(project, "case_001")
    state = load_state(project, "case_001")
    titles = " ".join(c.title.lower() for c in state.contradictions.values())
    assert "av" in titles or "scan" in titles or "clean" in titles
