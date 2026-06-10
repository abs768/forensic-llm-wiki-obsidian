"""Raw-source parsers.

Each parser turns a file's bytes into structured rows the extractors can work
with. Parsers know nothing about the wiki — they only know file formats.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SourceKind = Literal[
    "powershell_history",
    "registry_reg",
    "sysmon_csv",
    "network_csv",
    "defender_scan",
    "investigator_notes",
    "hash_reputation",
    "generic_text",
    "generic_csv",
    "generic_markdown",
]


@dataclass
class ParsedSource:
    path: str
    kind: SourceKind
    text: str
    rows: list[dict] | None = None  # populated for CSV files
    sections: list[dict] | None = None  # populated for registry files


def detect_kind(path: Path) -> SourceKind:
    """Detect file kind from its name and contents.

    We use the filename hints first because forensic file names are usually
    purposeful, then fall back to extension/contents.
    """
    name = path.name.lower()
    suffix = path.suffix.lower()

    if "powershell" in name and ("history" in name or "console" in name):
        return "powershell_history"
    if suffix == ".reg" or "registry" in name:
        return "registry_reg"
    if "sysmon" in name and suffix == ".csv":
        return "sysmon_csv"
    if ("network" in name or "netflow" in name or "conn" in name) and suffix == ".csv":
        return "network_csv"
    if "defender" in name or "av_scan" in name or "antivirus" in name:
        return "defender_scan"
    if "hash" in name and ("reputation" in name or "virustotal" in name or "rep" in name):
        return "hash_reputation"
    if "reputation" in name:
        return "hash_reputation"
    if "investigator" in name or "analyst" in name or "notes" in name:
        return "investigator_notes"
    if suffix == ".csv":
        return "generic_csv"
    if suffix in {".md", ".markdown"}:
        return "generic_markdown"
    return "generic_text"


def parse(path: Path) -> ParsedSource:
    text = path.read_text(encoding="utf-8", errors="replace")
    kind = detect_kind(path)
    rows = None
    sections = None

    if kind in {"sysmon_csv", "network_csv", "generic_csv"}:
        rows = _parse_csv(text)
    elif kind == "registry_reg":
        sections = _parse_reg(text)

    return ParsedSource(
        path=str(path),
        kind=kind,
        text=text,
        rows=rows,
        sections=sections,
    )


def _parse_csv(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    return [
        {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k}
        for row in reader
    ]


_REG_HEADER = re.compile(r"^\[([^\]]+)\]\s*$")
_REG_ENTRY = re.compile(r'^"(?P<name>[^"]+)"\s*=\s*(?P<value>.+?)\s*$')


def _parse_reg(text: str) -> list[dict]:
    sections: list[dict] = []
    current: dict | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lower().startswith("windows registry editor"):
            continue
        header = _REG_HEADER.match(line)
        if header:
            current = {"key": header.group(1), "values": []}
            sections.append(current)
            continue
        entry = _REG_ENTRY.match(line)
        if entry and current is not None:
            value = entry.group("value")
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
            current["values"].append({"name": entry.group("name"), "value": value})
    return sections
