"""Build a GraphRAG-lite ``Graph`` from the existing structured indexes.

We never call the LLM here. Edges are derived deterministically from:

  - ``entities.json`` (mentioned_in, related_to via shared sources)
  - ``events.json``   (spawned, connected_to, references)
  - ``claims.json``   (supports, contradicts)

The graph is written to:

  - ``wiki/cases/<case>/.fw/graph.json``   structured (Pydantic)
  - ``wiki/cases/<case>/.fw/graph.md``     human-readable summary
  - ``wiki/cases/<case>/.fw/graph.mmd``    Mermaid diagram source
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from ..index import claims_path, entities_path, events_path
from ..schemas import Graph, GraphEdge, GraphNode, GraphNodeType
from ..wiki_io import fw_dir


def graph_path(project_root: Path, case_id: str) -> Path:
    return fw_dir(project_root, case_id) / "graph.json"


def graph_md_path(project_root: Path, case_id: str) -> Path:
    return fw_dir(project_root, case_id) / "graph.md"


def graph_mmd_path(project_root: Path, case_id: str) -> Path:
    return fw_dir(project_root, case_id) / "graph.mmd"


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #


_SPAWN_RE = re.compile(
    r"^(?P<parent>[A-Za-z0-9_.\-]+\.exe) spawned (?P<child>[A-Za-z0-9_.\-]+\.exe)",
    re.IGNORECASE,
)
_CONNECT_RE = re.compile(
    r"(?P<proc>[A-Za-z0-9_.\-]+\.exe) connected to "
    r"(?P<ip>(?:\d{1,3}\.){3}\d{1,3}):(?P<port>\d+)",
    re.IGNORECASE,
)
_REG_VALUE_RE = re.compile(
    r"Registry value '(?P<name>[^']+)' set under (?P<key>[^=]+?) ?= ?(?P<value>.+)$",
    re.IGNORECASE,
)
_EXE_IN_TEXT_RE = re.compile(r"([A-Za-z0-9_.\-]+\.exe)")


def build_graph(project_root: Path, case_id: str) -> Graph:
    """Derive a graph from the case's existing structured indexes."""
    entities = _read_json(entities_path(project_root, case_id))
    events = _read_json(events_path(project_root, case_id))
    claims = _read_json(claims_path(project_root, case_id))

    graph = Graph(case_id=case_id)
    by_id: dict[str, GraphNode] = {}

    def add_node(node_id: str, node_type: GraphNodeType, label: str) -> GraphNode:
        existing = by_id.get(node_id)
        if existing:
            return existing
        node = GraphNode(id=node_id, type=node_type, label=label)
        by_id[node_id] = node
        graph.nodes.append(node)
        return node

    seen_edges: set[tuple[str, str, str]] = set()

    def add_edge(src: str, tgt: str, edge_type: str, evidence: str | None = None) -> None:
        key = (src, tgt, edge_type)
        if key in seen_edges or src not in by_id or tgt not in by_id:
            return
        graph.edges.append(GraphEdge(
            source=src, target=tgt, type=edge_type,  # type: ignore[arg-type]
            evidence=evidence,
        ))
        seen_edges.add(key)

    # --- entity nodes ---
    entity_node_id_by_value: dict[tuple[str, str], str] = {}
    for ent in entities:
        node_type = _normalise_entity_type(ent["entity_type"])
        node_id = _entity_id(node_type, ent["value"])
        add_node(node_id, node_type, ent["value"])
        entity_node_id_by_value[(ent["entity_type"].lower(), ent["value"].lower())] = node_id

        for sp in ent.get("source_paths", []):
            sid = _source_id(sp)
            add_node(sid, "source", _basename(sp))
            add_edge(node_id, sid, "mentioned_in", evidence=sp)

    # --- entity ↔ entity related_to via shared source ---
    by_source: dict[str, set[str]] = defaultdict(set)
    for ent in entities:
        node_type = _normalise_entity_type(ent["entity_type"])
        node_id = _entity_id(node_type, ent["value"])
        for sp in ent.get("source_paths", []):
            by_source[sp].add(node_id)
    for sp, ids in by_source.items():
        ids_list = sorted(ids)
        for i, a in enumerate(ids_list):
            for b in ids_list[i + 1:]:
                add_edge(a, b, "related_to", evidence=sp)

    # --- event-derived edges ---
    for ev in events:
        desc = ev["description"]
        sp = ev["source_path"]
        sid = _source_id(sp)
        if sid not in by_id:
            add_node(sid, "source", _basename(sp))
        _scan_event_for_spawn(desc, sp, add_node, add_edge)
        _scan_event_for_connect(desc, sp, add_node, add_edge)
        _scan_event_for_registry(desc, sp, add_node, add_edge)

    # --- claim nodes + supports/contradicts edges ---
    for cl in claims:
        cid = cl["claim_id"]
        node_type = "hypothesis" if cl["claim_type"] == "hypothesis" else "claim"
        add_node(cid, node_type, cl["claim_text"][:80])
        for s in cl.get("supporting_evidence", []):
            sp = s["source_path"]
            sid = _source_id(sp)
            add_node(sid, "source", _basename(sp))
            add_edge(cid, sid, "supports", evidence=sp)
        for s in cl.get("contradicting_evidence", []):
            sp = s["source_path"]
            sid = _source_id(sp)
            add_node(sid, "source", _basename(sp))
            add_edge(cid, sid, "contradicts", evidence=sp)

    return graph


# --------------------------------------------------------------------------- #
# Save
# --------------------------------------------------------------------------- #


def save_graph(project_root: Path, graph: Graph) -> dict[str, Path]:
    fw_dir(project_root, graph.case_id).mkdir(parents=True, exist_ok=True)
    jp = graph_path(project_root, graph.case_id)
    mp = graph_md_path(project_root, graph.case_id)
    pp = graph_mmd_path(project_root, graph.case_id)
    jp.write_text(graph.model_dump_json(indent=2))
    mp.write_text(_format_graph_md(graph))
    from .graph_export import to_mermaid
    pp.write_text(to_mermaid(graph))
    return {"graph.json": jp, "graph.md": mp, "graph.mmd": pp}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _read_json(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return json.loads(p.read_text())


def _basename(path: str) -> str:
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def _source_id(path: str) -> str:
    return f"source:{path}"


def _entity_id(node_type: str, value: str) -> str:
    return f"{node_type}:{value}"


def _normalise_entity_type(raw: str) -> GraphNodeType:
    mapping: dict[str, GraphNodeType] = {
        "process": "process",
        "file": "file",
        "user": "user",
        "host": "other",
        "ip": "ip_address",
        "domain": "domain",
        "registry_key": "registry_key",
        "command": "command",
        "hash": "other",
        "url": "domain",
        "other": "other",
    }
    return mapping.get(raw.lower(), "other")


def _scan_event_for_spawn(desc, source_path, add_node, add_edge) -> None:
    m = _SPAWN_RE.search(desc)
    if not m:
        return
    parent = m.group("parent")
    child = m.group("child")
    pid = _entity_id("process", parent)
    cid = _entity_id("file", child)
    add_node(pid, "process", parent)
    add_node(cid, "file", child)
    add_edge(pid, cid, "spawned", evidence=source_path)


def _scan_event_for_connect(desc, source_path, add_node, add_edge) -> None:
    for m in _CONNECT_RE.finditer(desc):
        proc = m.group("proc")
        ip = m.group("ip")
        pid = _entity_id("process", proc)
        ip_id = _entity_id("ip_address", ip)
        add_node(pid, "process", proc)
        add_node(ip_id, "ip_address", ip)
        add_edge(pid, ip_id, "connected_to", evidence=source_path)


def _scan_event_for_registry(desc, source_path, add_node, add_edge) -> None:
    m = _REG_VALUE_RE.search(desc)
    if not m:
        return
    key = m.group("key").strip()
    value = m.group("value").strip()
    key_id = _entity_id("registry_key", key)
    add_node(key_id, "registry_key", key)
    for exe in _EXE_IN_TEXT_RE.findall(value):
        exe_id = _entity_id("file", exe)
        add_node(exe_id, "file", exe)
        add_edge(key_id, exe_id, "references", evidence=source_path)


def _format_graph_md(graph: Graph) -> str:
    lines = [
        f"# Relationship Graph — `{graph.case_id}`\n",
        f"_{len(graph.nodes)} nodes, {len(graph.edges)} edges. "
        "Derived deterministically from `.fw/{events,entities,claims}.json`._\n",
    ]

    by_type: dict[str, list[str]] = defaultdict(list)
    for n in graph.nodes:
        by_type[n.type].append(n.label)
    lines.append("## Nodes by type\n")
    for t in sorted(by_type):
        items = sorted(set(by_type[t]))
        lines.append(f"- **{t}** ({len(items)}): " + ", ".join(items[:12])
                     + (f", … and {len(items) - 12} more" if len(items) > 12 else ""))
    lines.append("")

    counts_by_edge: dict[str, int] = defaultdict(int)
    for e in graph.edges:
        counts_by_edge[e.type] += 1
    lines.append("## Edges by type\n")
    for t in sorted(counts_by_edge):
        lines.append(f"- **{t}**: {counts_by_edge[t]}")
    lines.append("")

    return "\n".join(lines)
