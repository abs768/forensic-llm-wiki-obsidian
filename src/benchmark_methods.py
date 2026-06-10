"""Four-way method benchmark: raw_rag, graph_rag_lite, llm_wiki, hybrid.

Same deterministic scoring pipeline as ``src/benchmark.py``, but every
question runs through four providers. Two extra metrics are reported:

  - ``relationship_coverage``: per provider, the pass rate on
    ``relationship_retrieval`` / ``multi_hop_relation`` questions.
  - ``narrative_state_quality``: per provider, the pass rate on
    ``current_investigation_assessment`` / ``hypothesis_evolution`` /
    ``final_report_accuracy`` questions.

GraphRAG-lite should win relationship coverage; LLM Wiki should win
narrative state quality; Hybrid should win at least one combined eval.
"""
from __future__ import annotations

import json
from pathlib import Path

from .compare_all import build_hybrid_answer
from .eval import evaluate_answer, load_eval_file
from .evolve import benchmark_case_dir
from .graph.graph_query import graph_query
from .query import answer_question, format_answer
from .rag import rag_query
from .schemas import (
    EvalCase,
    MethodBenchmarkRow,
    MethodBenchmarkSummary,
    MethodRowCheck,
)

METHODS = ("raw_rag", "graph_rag_lite", "llm_wiki", "hybrid")

_RELATIONSHIP_CATEGORIES = {"relationship_retrieval", "multi_hop_relation"}
_NARRATIVE_CATEGORIES = {
    "current_investigation_assessment",
    "hypothesis_evolution",
    "final_report_accuracy",
}
_CONTRADICTION_CATEGORIES = {"contradiction_detection"}


def benchmark_methods(
    project_root: Path,
    case_id: str,
    *,
    eval_filename: str | None = None,
) -> MethodBenchmarkSummary:
    cases = _load_eval_for_methods(project_root, case_id, eval_filename)
    rows: list[MethodBenchmarkRow] = []

    for case in cases:
        wiki_ans = answer_question(project_root, case_id, case.question)
        rag_ans = rag_query(project_root, case_id, case.question)
        graph_ans = graph_query(project_root, case_id, case.question)
        hybrid_ans = build_hybrid_answer(
            project_root, case_id, case.question, wiki_ans, graph_ans,
        )

        results: dict[str, MethodRowCheck] = {}
        for method, ans in (
            ("raw_rag", rag_ans),
            ("graph_rag_lite", graph_ans),
            ("llm_wiki", wiki_ans),
            ("hybrid", hybrid_ans),
        ):
            text = format_answer(ans)
            res, u, m = evaluate_answer(case, ans, text)
            results[method] = MethodRowCheck(
                method=method,  # type: ignore[arg-type]
                passed=res.passed,
                checks=res.checks,
                unsupported_failures=u,
                missing_source_failures=m,
                answer=text,
            )

        rows.append(MethodBenchmarkRow(
            question_id=case.id,
            question=case.question,
            category=case.category,
            expected_best_method=case.expected_best_method,
            results=results,
        ))

    summary = _summarise(case_id, rows, cases)
    _write_outputs(project_root, summary)
    return summary


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #


def _load_eval_for_methods(
    project_root: Path,
    case_id: str,
    eval_filename: str | None,
) -> list[EvalCase]:
    """Prefer evals/<case>_methods_eval.json (Phase 5); fall back to the
    Phase 2/3 case eval if the methods file is absent."""
    if eval_filename is None:
        explicit = project_root / "evals" / f"{case_id}_methods_eval.json"
        if explicit.exists():
            eval_filename = explicit.name
    if eval_filename:
        p = project_root / "evals" / eval_filename
        if p.exists():
            payload = json.loads(p.read_text())
            items = payload.get("items", payload)
            return [EvalCase.model_validate(x) for x in items]
    return load_eval_file(project_root, case_id)


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #


def _summarise(
    case_id: str,
    rows: list[MethodBenchmarkRow],
    cases: list[EvalCase],
) -> MethodBenchmarkSummary:
    summary = MethodBenchmarkSummary(case_id=case_id, total=len(rows), rows=rows)

    refusal_total = sum(1 for c in cases if c.expect_refusal)
    relationship_total = sum(1 for c in cases if c.category in _RELATIONSHIP_CATEGORIES)
    narrative_total = sum(1 for c in cases if c.category in _NARRATIVE_CATEGORIES)

    for method in METHODS:
        passed = sum(1 for r in rows if r.results[method].passed)
        unsupported = sum(r.results[method].unsupported_failures for r in rows)
        missing = sum(r.results[method].missing_source_failures for r in rows)

        refusal_ok = sum(
            1 for r, c in zip(rows, cases, strict=False)
            if c.expect_refusal and _is_refusal(r.results[method].answer)
        )
        contradiction_misses = sum(
            1 for r, c in zip(rows, cases, strict=False)
            if c.category in _CONTRADICTION_CATEGORIES and not r.results[method].passed
        )
        relationship_passed = sum(
            1 for r, c in zip(rows, cases, strict=False)
            if c.category in _RELATIONSHIP_CATEGORIES and r.results[method].passed
        )
        narrative_passed = sum(
            1 for r, c in zip(rows, cases, strict=False)
            if c.category in _NARRATIVE_CATEGORIES and r.results[method].passed
        )
        expected_best_wins = sum(
            1 for r, c in zip(rows, cases, strict=False)
            if c.expected_best_method == method and r.results[method].passed
        )

        summary.per_method[method] = {
            "passed": passed,
            "failed": summary.total - passed,
            "unsupported_failures": unsupported,
            "missing_source_failures": missing,
            "refusal_accuracy": (refusal_ok / refusal_total) if refusal_total else 0.0,
            "contradiction_misses": contradiction_misses,
            "relationship_coverage": (
                relationship_passed / relationship_total
                if relationship_total else 0.0
            ),
            "narrative_state_quality": (
                narrative_passed / narrative_total
                if narrative_total else 0.0
            ),
            "expected_best_wins": expected_best_wins,
        }
    return summary


def _is_refusal(text: str) -> bool:
    t = text.lower()
    return (
        "not confirmed" in t
        or t.lstrip().startswith("answer:\nno")
        or "\nno." in t
        or "\nno " in t
    )


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #


def _write_outputs(project_root: Path, summary: MethodBenchmarkSummary) -> None:
    bcd = benchmark_case_dir(project_root, summary.case_id)
    bcd.mkdir(parents=True, exist_ok=True)
    (bcd / "method_comparison.json").write_text(summary.model_dump_json(indent=2))
    (bcd / "method_comparison.md").write_text(format_method_markdown(summary))


def format_method_markdown(summary: MethodBenchmarkSummary) -> str:
    methods = METHODS
    out: list[str] = []
    out.append(f"# Method Comparison — `{summary.case_id}`\n")
    out.append(
        "Four providers were scored against the same eval set:\n\n"
        "1. **Raw RAG** — naive BM25 over raw_sources/.\n"
        "2. **GraphRAG-lite** — answers from the derived relationship graph.\n"
        "3. **LLM Wiki** — answers from the compiled investigation state.\n"
        "4. **Hybrid** — wiki assessment + graph relationship context.\n"
    )

    head = "| Metric | " + " | ".join(_pretty(m) for m in methods) + " |"
    align = "|---|" + "---:|" * len(methods)
    out.append("## Scoring summary\n")
    out.append(head)
    out.append(align)

    rows = [
        ("Total questions", lambda m: summary.total),
        ("Passed", lambda m: summary.per_method[m]["passed"]),
        ("Failed", lambda m: summary.per_method[m]["failed"]),
        ("Unsupported claim failures", lambda m: summary.per_method[m]["unsupported_failures"]),
        ("Missing source failures", lambda m: summary.per_method[m]["missing_source_failures"]),
        ("Contradiction misses", lambda m: summary.per_method[m]["contradiction_misses"]),
        ("Relationship coverage", lambda m: f"{summary.per_method[m]['relationship_coverage']:.2f}"),
        ("Narrative state quality", lambda m: f"{summary.per_method[m]['narrative_state_quality']:.2f}"),
        ("Refusal accuracy", lambda m: f"{summary.per_method[m]['refusal_accuracy']:.2f}"),
        ("Expected-best wins", lambda m: summary.per_method[m]["expected_best_wins"]),
    ]
    for label, fn in rows:
        out.append("| " + label + " | " + " | ".join(str(fn(m)) for m in methods) + " |")
    out.append("")

    out.append("## Per-question results\n")
    out.append("| ID | Category | Expected best | "
               + " | ".join(_pretty(m) for m in methods) + " |")
    out.append("|---|---|---|" + ":---:|" * len(methods))
    for r in summary.rows:
        cells = []
        for m in methods:
            mark = "PASS" if r.results[m].passed else "fail"
            cells.append(mark)
        out.append(
            f"| {r.question_id} | {r.category} | "
            f"{r.expected_best_method or '-'} | " + " | ".join(cells) + " |"
        )
    out.append("")

    out.append("## What to read out of this table\n")
    out.append(
        "- **Relationship coverage** should favour GraphRAG-lite "
        "(and Hybrid, which inherits it).\n"
        "- **Narrative state quality**, **refusal accuracy**, and "
        "**contradiction misses** should favour LLM Wiki and Hybrid.\n"
        "- **Hybrid** should win the most ``expected_best`` wins because "
        "it has both the graph context and the wiki's assessment.\n"
        "- Raw RAG is the foil. It is included to make the cost of "
        "'just retrieve' visible.\n"
    )
    return "\n".join(out)


def _pretty(m: str) -> str:
    return {
        "raw_rag": "Raw RAG",
        "graph_rag_lite": "GraphRAG-lite",
        "llm_wiki": "LLM Wiki",
        "hybrid": "Hybrid",
    }.get(m, m)
