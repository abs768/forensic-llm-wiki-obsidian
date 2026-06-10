"""Shared pytest fixtures: a temporary project tree pre-populated with the
demo case_001 raw sources. The original project's raw_sources/case_001 is
copied wholesale so tests exercise the real demo data.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A throwaway project tree mirroring the real raw_sources/, schema/, evals/."""
    (tmp_path / "raw_sources").mkdir(parents=True)
    (tmp_path / "wiki").mkdir(parents=True)
    (tmp_path / "schema").mkdir(parents=True)
    (tmp_path / "evals").mkdir(parents=True)

    src_raw_root = PROJECT_ROOT / "raw_sources"
    for case_dir in src_raw_root.iterdir():
        if not case_dir.is_dir() or case_dir.name.startswith("."):
            continue
        dst = tmp_path / "raw_sources" / case_dir.name
        shutil.copytree(case_dir, dst)

    src_schema = PROJECT_ROOT / "schema"
    for f in src_schema.iterdir():
        if f.is_file() and not f.name.startswith("."):
            shutil.copy(f, tmp_path / "schema" / f.name)

    src_evals = PROJECT_ROOT / "evals"
    if src_evals.exists():
        for f in src_evals.iterdir():
            if f.is_file() and not f.name.startswith("."):
                shutil.copy(f, tmp_path / "evals" / f.name)

    return tmp_path


@pytest.fixture
def empty_project(tmp_path: Path) -> Path:
    """Project tree with empty raw_sources for the case (no files)."""
    (tmp_path / "raw_sources" / "case_001").mkdir(parents=True)
    (tmp_path / "wiki").mkdir(parents=True)
    return tmp_path
