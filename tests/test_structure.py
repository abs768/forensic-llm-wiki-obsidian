"""Wiki folder structure is created correctly by ensure_case_structure
and the ingest pipeline."""
from __future__ import annotations

from pathlib import Path

from src.ingest import ingest_case
from src.wiki_io import REQUIRED_PAGES, case_dir, ensure_case_structure


def test_ensure_case_structure_creates_case_dir(empty_project: Path) -> None:
    cdir = ensure_case_structure(empty_project, "case_001")
    assert cdir.exists()
    assert cdir == case_dir(empty_project, "case_001")
    assert (empty_project / "wiki" / "index.md").exists()


def test_ingest_creates_all_required_pages(project: Path) -> None:
    ingest_case(project, "case_001")
    cdir = case_dir(project, "case_001")
    for name in REQUIRED_PAGES:
        assert (cdir / name).exists(), f"missing {name}"
