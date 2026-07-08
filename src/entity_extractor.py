"""Pull Entity records out of parsed sources.

The extractor is deterministic and shared by both mock-LLM and real-LLM
modes. In live mode the LLM may add additional entities; here we capture the
ones that are unambiguous (anything literally present in the file).
"""
from __future__ import annotations

import re

from .parsers import ParsedSource
from .schemas import Citation, Entity


def _basename(path: str) -> str:
    """Cross-platform basename: handles Windows-style backslashes on POSIX."""
    return path.replace("\\", "/").rsplit("/", 1)[-1]


_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_DOMAIN_RE = re.compile(
    r"\b(?!\d+\.\d+\.\d+\.\d+\b)([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z]{2,}\b"
)
_EXE_RE = re.compile(r"\b([A-Za-z0-9_.\-]+\.exe)\b")
_USER_RE = re.compile(r"\b([A-Z][A-Z0-9_-]{2,}\\[a-zA-Z][a-zA-Z0-9_.\-]+)\b")


def extract_entities(source: ParsedSource) -> list[Entity]:
    cite = Citation(kind="source", target=source.path)
    appears = [source.path]

    by_key: dict[str, Entity] = {}

    def add(e: Entity) -> None:
        existing = by_key.get(e.key)
        if existing is None:
            by_key[e.key] = e
            return
        for r in e.related:
            if r not in existing.related:
                existing.related.append(r)
        for ap in e.appears_in:
            if ap not in existing.appears_in:
                existing.appears_in.append(ap)

    if source.kind == "sysmon_csv" and source.rows:
        for row in source.rows:
            for col in ("image", "parent_image"):
                v = row.get(col)
                if v:
                    proc = _basename(v)
                    add(Entity(type="process", value=proc, appears_in=appears, citations=[cite]))
                    if v != proc:
                        add(Entity(type="file", value=v, appears_in=appears, citations=[cite]))
            user = row.get("user")
            if user:
                add(Entity(type="user", value=user, appears_in=appears, citations=[cite]))
            cmd = row.get("command_line")
            if cmd:
                add(Entity(type="command", value=cmd, appears_in=appears, citations=[cite]))
                for ip in _IP_RE.findall(cmd):
                    add(Entity(type="ip", value=ip, appears_in=appears, citations=[cite]))

    elif source.kind == "network_csv" and source.rows:
        for row in source.rows:
            for col in ("remote_address", "local_address"):
                v = row.get(col)
                if v:
                    add(Entity(type="ip", value=v, appears_in=appears, citations=[cite]))
            row_proc = row.get("process")
            if row_proc:
                add(Entity(type="process", value=row_proc, appears_in=appears, citations=[cite]))

    elif source.kind == "registry_reg" and source.sections:
        for section in source.sections:
            add(Entity(type="registry_key", value=section["key"], appears_in=appears, citations=[cite]))
            for entry in section.get("values", []):
                v = entry["value"]
                for exe in _EXE_RE.findall(v):
                    add(Entity(type="file", value=exe, appears_in=appears, citations=[cite]))

    # Catch-all: scrape the raw text for anything left.
    for ip in _IP_RE.findall(source.text):
        add(Entity(type="ip", value=ip, appears_in=appears, citations=[cite]))
    # _DOMAIN_RE.findall returns the last capture group; iterate with
    # finditer below so we get the full match each time.
    for match in _DOMAIN_RE.finditer(source.text):
        domain = match.group(0)
        if domain.lower().endswith((".exe", ".reg", ".csv", ".txt", ".md")):
            continue
        add(Entity(type="domain", value=domain, appears_in=appears, citations=[cite]))
    process_basenames = {e.value.lower() for e in by_key.values() if e.type == "process"}
    for exe in _EXE_RE.findall(source.text):
        if exe.lower() == "powershell.exe":
            continue  # added above when relevant
        if exe.lower() in process_basenames:
            continue  # already represented as a process entity
        add(Entity(type="file", value=exe, appears_in=appears, citations=[cite]))
    for user in _USER_RE.findall(source.text):
        add(Entity(type="user", value=user, appears_in=appears, citations=[cite]))

    return list(by_key.values())
