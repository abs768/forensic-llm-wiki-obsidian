"""Side-by-side comparison: compiled wiki query vs. raw-source RAG baseline.

The point of this command is pedagogical: print both answers in the same
terminal so the user can see what compounded knowledge buys them.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .query import answer_question, format_answer
from .rag import rag_query
from .schemas import QueryAnswer


@dataclass
class Comparison:
    question: str
    wiki: QueryAnswer
    rag: QueryAnswer


def compare(project_root: Path, case_id: str, question: str) -> Comparison:
    wiki = answer_question(project_root, case_id, question)
    rag = rag_query(project_root, case_id, question)
    return Comparison(question=question, wiki=wiki, rag=rag)


def format_comparison(c: Comparison) -> str:
    bar = "=" * 78
    lines = [bar]
    lines.append(f"QUESTION: {c.question}")
    lines.append(bar)
    lines.append("")
    lines.append("[1] Forensic LLM Wiki — compiled answer")
    lines.append("-" * 78)
    lines.append(format_answer(c.wiki))
    lines.append("")
    lines.append("[2] Naive raw-source RAG baseline")
    lines.append("-" * 78)
    lines.append(format_answer(c.rag))
    lines.append("")
    lines.append(bar)
    lines.append("Compare the two answers:")
    lines.append("- The wiki answer states a position, lists hypotheses, surfaces")
    lines.append("  contradictions, and assigns confidence.")
    lines.append("- The RAG baseline retrieves matching snippets and stops there.")
    lines.append("  It does not reconcile conflicting evidence.")
    return "\n".join(lines)
