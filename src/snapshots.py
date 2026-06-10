"""Snapshots of a case wiki.

Each snapshot is a flat copy of ``wiki/cases/<case_id>/`` (markdown pages +
``.fw/`` sidecar) saved under ``wiki_snapshots/<case_id>/<name>/``. The
``evolve`` command takes one snapshot after each step so we can diff the
wiki between successive evidence drops.

Snapshots are inert archives. They are never read back into the live wiki
state — they exist for human inspection and for the ``diff-snapshots``
command.
"""
from __future__ import annotations

import difflib
import shutil
from pathlib import Path

from .wiki_io import REQUIRED_PAGES, case_dir


def snapshots_root(project_root: Path) -> Path:
    return project_root / "wiki_snapshots"


def snapshots_case_dir(project_root: Path, case_id: str) -> Path:
    return snapshots_root(project_root) / case_id


def snapshot_dir(project_root: Path, case_id: str, name: str) -> Path:
    return snapshots_case_dir(project_root, case_id) / name


def take_snapshot(project_root: Path, case_id: str, name: str) -> Path:
    src = case_dir(project_root, case_id)
    if not src.exists():
        raise FileNotFoundError(f"Case wiki not found at {src}")
    dst = snapshot_dir(project_root, case_id, name)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst


def list_snapshots(project_root: Path, case_id: str) -> list[str]:
    sd = snapshots_case_dir(project_root, case_id)
    if not sd.exists():
        return []
    return sorted(p.name for p in sd.iterdir() if p.is_dir())


def diff_snapshots(
    project_root: Path,
    case_id: str,
    name_a: str,
    name_b: str,
) -> dict[str, str]:
    """Per-page unified diff between two snapshots. Only ``REQUIRED_PAGES``
    are compared — sidecar JSON is intentionally skipped because its diff is
    huge and unreadable; use the markdown to see what actually changed.
    """
    a = snapshot_dir(project_root, case_id, name_a)
    b = snapshot_dir(project_root, case_id, name_b)
    if not a.exists():
        raise FileNotFoundError(f"Snapshot not found: {a}")
    if not b.exists():
        raise FileNotFoundError(f"Snapshot not found: {b}")

    out: dict[str, str] = {}
    for name in REQUIRED_PAGES:
        ap, bp = a / name, b / name
        old = ap.read_text() if ap.exists() else ""
        new = bp.read_text() if bp.exists() else ""
        if old == new:
            continue
        diff = "".join(difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"a/{name}",
            tofile=f"b/{name}",
            n=3,
        ))
        out[name] = diff
    return out


def format_diff(case_id: str, name_a: str, name_b: str, diffs: dict[str, str]) -> str:
    if not diffs:
        return f"No markdown differences between '{name_a}' and '{name_b}'."
    lines = [f"Diff: {case_id}/{name_a} → {case_id}/{name_b}", ""]
    for name, diff in diffs.items():
        lines.append(f"--- Page changed: {name} ---")
        lines.append(diff.rstrip())
        lines.append("")
    return "\n".join(lines)
