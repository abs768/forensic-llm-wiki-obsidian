"""Answer a relationship question using the GraphRAG-lite graph.

The graph cannot reason about confidence, contradictions, or
investigation state. It can only report what is connected to what — and
that is exactly the question this provider is good at.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..schemas import Graph, GraphEdge, GraphNode, QueryAnswer
from .graph_builder import graph_path


@dataclass
class GraphAnswer:
    question: str
    matched_node: GraphNode | None
    related: list[tuple[GraphEdge, GraphNode]] = field(default_factory=list)


def load_graph(project_root: Path, case_id: str) -> Graph | None:
    p = graph_path(project_root, case_id)
    if not p.exists():
        return None
    return Graph.model_validate_json(p.read_text())


def graph_query(project_root: Path, case_id: str, question: str) -> QueryAnswer:
    """Return a :class:`QueryAnswer` so this provider plugs into compare-all."""
    graph = load_graph(project_root, case_id)
    if graph is None or not graph.nodes:
        return QueryAnswer(
            question=question,
            answer="The relationship graph has not been built yet. Run `fw.py graph-build <case>`.",
            classification="fact",
            confidence="Low",
            insufficient=True,
        )

    matched = _match_node(graph, question)
    if matched is None:
        return QueryAnswer(
            question=question,
            answer=(
                "The relationship graph contains no node matching the question. "
                "GraphRAG-lite answers entity-relationship questions; rephrase "
                "to mention a specific artifact (process, file, IP, registry key)."
            ),
            classification="fact",
            confidence="Low",
            insufficient=True,
        )

    neighbours = graph.neighbors(matched.id)
    if not neighbours:
        return QueryAnswer(
            question=question,
            answer=f"{matched.label} has no recorded relationships in the graph.",
            classification="fact",
            confidence="Low",
        )

    lines = [f"{matched.label} is related to:", ""]
    related_labels: set[str] = set()
    sources: set[str] = set()
    for edge, other in neighbours:
        kind = edge.type.replace("_", " ")
        lines.append(f"- {other.label} ({other.type}) — {kind}"
                     + (f" (evidence: {edge.evidence})" if edge.evidence else ""))
        related_labels.add(other.label)
        if edge.evidence:
            sources.add(edge.evidence)
    lines.append("")
    lines.append(
        "This graph query shows relationships only. It does not determine "
        "whether malware is confirmed; for current assessment use the LLM "
        "Wiki query."
    )
    return QueryAnswer(
        question=question,
        answer="\n".join(lines),
        assessment=(
            f"GraphRAG-lite: {len(neighbours)} relationship(s) for "
            f"{matched.label}. Pure relationship structure — no synthesis, "
            "no confidence."
        ),
        classification="fact",
        confidence="Medium",
        supporting_pages=["[[entities]]"],
        supporting_sources=sorted(sources),
        evidence_items=[
            f"{matched.label} → {other.label} ({e.type})"
            for e, other in neighbours
        ],
    )


# --------------------------------------------------------------------------- #
# Node matching
# --------------------------------------------------------------------------- #


def _match_node(graph: Graph, question: str) -> GraphNode | None:
    """Find the node whose label appears in the question. Prefer the longest
    match so that ``DeskRest.exe`` wins over ``DeskRest``."""
    q = question.lower()
    candidates: list[GraphNode] = []
    for n in graph.nodes:
        if not n.label:
            continue
        if n.label.lower() in q:
            candidates.append(n)
    if not candidates:
        return None
    return max(candidates, key=lambda n: len(n.label))


def format_graph_answer(ans: QueryAnswer) -> str:
    from ..query import format_answer
    return format_answer(ans)
