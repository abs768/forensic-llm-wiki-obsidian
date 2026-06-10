"""Four-way comparator: raw RAG, GraphRAG-lite, LLM Wiki, hybrid.

The point is pedagogical. Print all four answers in one terminal so the
reader can see *what each method is good at*:

  - Raw RAG returns matching snippets.
  - GraphRAG-lite enumerates relationships.
  - LLM Wiki returns the compiled assessment with refusal discipline.
  - Hybrid combines the wiki's assessment with the graph's relationship
    structure.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .graph.graph_query import graph_query, load_graph
from .query import answer_question, format_answer
from .rag import rag_query
from .schemas import Graph, QueryAnswer


@dataclass
class FourWay:
    question: str
    raw_rag: QueryAnswer
    graph_rag_lite: QueryAnswer
    llm_wiki: QueryAnswer
    hybrid: QueryAnswer


def compare_all(project_root: Path, case_id: str, question: str) -> FourWay:
    raw = rag_query(project_root, case_id, question)
    gph = graph_query(project_root, case_id, question)
    wiki = answer_question(project_root, case_id, question)
    hybrid = build_hybrid_answer(project_root, case_id, question, wiki, gph)
    return FourWay(question=question, raw_rag=raw, graph_rag_lite=gph,
                   llm_wiki=wiki, hybrid=hybrid)


def build_hybrid_answer(
    project_root: Path,
    case_id: str,
    question: str,
    wiki_ans: QueryAnswer,
    graph_ans: QueryAnswer,
) -> QueryAnswer:
    """Combine the wiki answer with relevant graph context.

    We start with the wiki answer because the *assessment* is the harder
    thing to produce; then we splice in a relationship block from the
    graph for any entity whose label appears in either the question or
    the wiki's evidence_items.
    """
    graph = load_graph(project_root, case_id)
    rel_block = ""
    if graph is not None:
        rel_block = _gather_related_entities(
            graph,
            interest_text=question + " " + " ".join(wiki_ans.evidence_items),
        )

    parts: list[str] = []
    parts.append(
        "Hybrid (LLM Wiki + GraphRAG-lite) answer. The wiki's compiled "
        "assessment is shown first; relationship context from the graph "
        "is appended below."
    )
    parts.append("")
    parts.append("### Wiki assessment")
    parts.append(format_answer(wiki_ans))
    if rel_block:
        parts.append("")
        parts.append("### Graph relationship context")
        parts.append(rel_block)
    else:
        parts.append("")
        parts.append("### Graph relationship context")
        parts.append(
            "_(no specific entity matched the question; relationship "
            "graph not consulted for this answer)_"
        )

    supporting_sources = sorted(
        set(wiki_ans.supporting_sources) | set(graph_ans.supporting_sources)
    )
    supporting_pages = sorted(
        set(wiki_ans.supporting_pages) | set(graph_ans.supporting_pages)
        | {"[[entities]]"}
    )
    evidence_items = wiki_ans.evidence_items + (
        ["graph: " + e for e in graph_ans.evidence_items]
        if graph_ans.evidence_items else []
    )
    return QueryAnswer(
        question=question,
        answer="\n".join(parts),
        assessment=(
            wiki_ans.assessment
            + " Augmented with relationship context from the graph."
        ).strip(),
        classification=wiki_ans.classification,
        confidence=wiki_ans.confidence,
        supporting_pages=supporting_pages,
        supporting_sources=supporting_sources,
        contradicting_evidence=wiki_ans.contradicting_evidence,
        caveats=wiki_ans.caveats,
        evidence_items=evidence_items,
    )


def _gather_related_entities(graph: Graph, *, interest_text: str) -> str:
    """For every graph node whose label appears in the interest text,
    list its neighbours. Cap each list to keep the block readable."""
    interest = interest_text.lower()
    blocks: list[str] = []
    seen_nodes: set[str] = set()
    for node in graph.nodes:
        if not node.label or node.id in seen_nodes:
            continue
        if node.label.lower() not in interest:
            continue
        seen_nodes.add(node.id)
        neigh = graph.neighbors(node.id)
        if not neigh:
            continue
        blocks.append(f"- **{node.label}** ({node.type}) — {len(neigh)} relationship(s):")
        for edge, other in neigh[:5]:
            blocks.append(f"    - {edge.type.replace('_', ' ')} → {other.label}")
        if len(neigh) > 5:
            blocks.append(f"    - … and {len(neigh) - 5} more")
    return "\n".join(blocks)


def format_four_way(c: FourWay) -> str:
    bar = "=" * 78
    out: list[str] = []
    out.append(bar)
    out.append(f"Question:\n  {c.question}")
    out.append(bar)
    out.append("")
    out.append("[1] Raw RAG Answer")
    out.append("-" * 78)
    out.append(format_answer(c.raw_rag))
    out.append("")
    out.append("[2] GraphRAG-lite Answer")
    out.append("-" * 78)
    out.append(format_answer(c.graph_rag_lite))
    out.append("")
    out.append("[3] LLM Wiki Answer")
    out.append("-" * 78)
    out.append(format_answer(c.llm_wiki))
    out.append("")
    out.append("[4] Hybrid Wiki + Graph Answer")
    out.append("-" * 78)
    out.append(format_answer(c.hybrid))
    out.append("")
    out.append(bar)
    out.append("Takeaway:")
    out.append("  - Raw RAG retrieves snippets.")
    out.append("  - GraphRAG-lite shows relationships.")
    out.append("  - LLM Wiki gives the current investigation assessment.")
    out.append("  - Hybrid combines relationship structure with maintained case state.")
    return "\n".join(out)
