"""Export a :class:`Graph` to formats other tools can render.

Mermaid first (because GitHub renders it natively); a JSON dump is
available via ``graph.model_dump_json`` and a markdown summary lives at
``graph.md``.
"""
from __future__ import annotations

import re

from ..schemas import Graph

_MERMAID_ID_RE = re.compile(r"[^A-Za-z0-9_]")


def _mermaid_id(node_id: str) -> str:
    """Mermaid IDs must be alphanumeric + underscore."""
    cleaned = _MERMAID_ID_RE.sub("_", node_id)
    if not cleaned or cleaned[0].isdigit():
        cleaned = "n_" + cleaned
    return cleaned


def to_mermaid(graph: Graph, *, max_edges: int = 200) -> str:
    """Render the graph as a Mermaid ``graph TD`` diagram.

    Some graphs grow large; we cap at ``max_edges`` to keep the diagram
    readable. The truncated edges are still in ``graph.json``.
    """
    lines = ["graph TD"]
    label_by_id: dict[str, str] = {}
    for n in graph.nodes:
        mid = _mermaid_id(n.id)
        label_by_id[n.id] = mid
        label = n.label.replace("\"", "'")
        lines.append(f"    {mid}[\"{label}<br/><i>{n.type}</i>\"]")

    truncated = max(0, len(graph.edges) - max_edges)
    for e in graph.edges[:max_edges]:
        src = label_by_id.get(e.source)
        tgt = label_by_id.get(e.target)
        if not src or not tgt:
            continue
        lines.append(f"    {src} -->|{e.type}| {tgt}")

    if truncated:
        lines.append(f"    %% truncated {truncated} additional edge(s) for readability")
    return "\n".join(lines) + "\n"
