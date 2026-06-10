"""Benchmark: score the compiled wiki against the naive raw-source baseline.

For every question in the case's eval file we run two providers:

  1. The compiled-wiki ``answer_question`` (Phase 1/2 product).
  2. The naive ``rag_query`` (Phase 2 baseline).

Each answer is scored with the same eval checks. The output is a JSON
results file and a markdown report with a side-by-side scoring table.

The benchmark uses simple deterministic scoring (must_include / must_not /
required_sources / refusal / category-bucketed). No LLM-as-judge.

Two derived metrics worth pointing out:

  - "contradiction misses" — for any question in the
    ``contradiction_detection`` category, did the provider fail to mention
    at least one piece of contradicting evidence? Wiki should win this
    consistently; RAG has no notion of contradictions.
  - "refusal accuracy" — for any question with ``expect_refusal=true``,
    did the provider's answer refuse? Reported as a fraction in [0, 1].
"""
from __future__ import annotations

from pathlib import Path

from .eval import evaluate_answer, load_eval_file
from .evolve import benchmark_case_dir
from .query import answer_question, format_answer
from .rag import rag_query
from .schemas import BenchmarkRow, BenchmarkSummary

_CONTRADICTION_KEYWORDS = (
    "defender", "contradict", "clean scan", "hash reputation",
    "inconclusive", "no threats", "investigator suspicion",
)


def benchmark_case(project_root: Path, case_id: str) -> BenchmarkSummary:
    cases = load_eval_file(project_root, case_id)
    rows: list[BenchmarkRow] = []
    wiki_unsupported = 0
    rag_unsupported = 0
    wiki_missing = 0
    rag_missing = 0
    wiki_contra_miss = 0
    rag_contra_miss = 0
    refusal_total = 0
    wiki_refusal_ok = 0
    rag_refusal_ok = 0

    for case in cases:
        wiki_ans = answer_question(project_root, case_id, case.question)
        wiki_text = format_answer(wiki_ans)
        rag_ans = rag_query(project_root, case_id, case.question)
        rag_text = format_answer(rag_ans)

        wiki_result, wu, wm = evaluate_answer(case, wiki_ans, wiki_text)
        rag_result, ru, rm = evaluate_answer(case, rag_ans, rag_text)
        wiki_unsupported += wu
        rag_unsupported += ru
        wiki_missing += wm
        rag_missing += rm

        if case.category == "contradiction_detection":
            # A "miss" here means the provider failed the eval for a question
            # whose whole point is to surface a known contradiction.
            if not wiki_result.passed:
                wiki_contra_miss += 1
            if not rag_result.passed:
                rag_contra_miss += 1

        if case.expect_refusal:
            refusal_total += 1
            if _is_refusal(wiki_text, wiki_ans):
                wiki_refusal_ok += 1
            if _is_refusal(rag_text, rag_ans):
                rag_refusal_ok += 1

        rows.append(BenchmarkRow(
            question_id=case.id,
            question=case.question,
            category=case.category,
            wiki_passed=wiki_result.passed,
            rag_passed=rag_result.passed,
            wiki_checks=wiki_result.checks,
            rag_checks=rag_result.checks,
            wiki_answer=wiki_text,
            rag_answer=rag_text,
            wiki_unsupported_failures=wu,
            rag_unsupported_failures=ru,
            wiki_missing_source_failures=wm,
            rag_missing_source_failures=rm,
        ))

    summary = BenchmarkSummary(
        case_id=case_id,
        total=len(rows),
        wiki_passed=sum(1 for r in rows if r.wiki_passed),
        wiki_failed=sum(1 for r in rows if not r.wiki_passed),
        rag_passed=sum(1 for r in rows if r.rag_passed),
        rag_failed=sum(1 for r in rows if not r.rag_passed),
        wiki_unsupported_failures=wiki_unsupported,
        rag_unsupported_failures=rag_unsupported,
        wiki_missing_source_failures=wiki_missing,
        rag_missing_source_failures=rag_missing,
        wiki_contradiction_misses=wiki_contra_miss,
        rag_contradiction_misses=rag_contra_miss,
        wiki_refusal_accuracy=(wiki_refusal_ok / refusal_total) if refusal_total else 0.0,
        rag_refusal_accuracy=(rag_refusal_ok / refusal_total) if refusal_total else 0.0,
        rows=rows,
    )

    _write_results(project_root, summary)
    return summary


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _mentions_contradiction(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in _CONTRADICTION_KEYWORDS) and (
        "contradict" in t or "defender" in t or "inconclusive" in t
    )


def _is_refusal(text: str, ans) -> bool:
    t = text.lower()
    return (
        getattr(ans, "insufficient", False)
        or "not confirmed" in t
        or t.lstrip().startswith("answer:\nno")
        or "\nno." in t
        or "\nno " in t
    )


def _write_results(project_root: Path, summary: BenchmarkSummary) -> None:
    bcd = benchmark_case_dir(project_root, summary.case_id)
    bcd.mkdir(parents=True, exist_ok=True)
    (bcd / "results.json").write_text(summary.model_dump_json(indent=2))
    (bcd / "results.md").write_text(format_markdown(summary))


def format_markdown(summary: BenchmarkSummary) -> str:
    out: list[str] = []
    out.append(f"# Benchmark Results — `{summary.case_id}`\n")
    out.append(
        "Two providers were scored against the same eval set:\n\n"
        "1. **LLM Wiki** — the compiled wiki produced by `fw.py ingest`.\n"
        "2. **Raw RAG** — naive BM25-style retrieval over `raw_sources/`.\n"
    )

    out.append("## Scoring summary\n")
    out.append("| Metric | Raw RAG | LLM Wiki |")
    out.append("|---|---:|---:|")
    out.append(f"| Total questions | {summary.total} | {summary.total} |")
    out.append(f"| Passed | {summary.rag_passed} | {summary.wiki_passed} |")
    out.append(f"| Failed | {summary.rag_failed} | {summary.wiki_failed} |")
    out.append(
        f"| Unsupported claim failures | "
        f"{summary.rag_unsupported_failures} | "
        f"{summary.wiki_unsupported_failures} |"
    )
    out.append(
        f"| Missing source failures | "
        f"{summary.rag_missing_source_failures} | "
        f"{summary.wiki_missing_source_failures} |"
    )
    out.append(
        f"| Contradiction misses | "
        f"{summary.rag_contradiction_misses} | "
        f"{summary.wiki_contradiction_misses} |"
    )
    out.append(
        f"| Refusal accuracy | "
        f"{summary.rag_refusal_accuracy:.2f} | "
        f"{summary.wiki_refusal_accuracy:.2f} |"
    )
    out.append("")

    out.append("## Per-question results\n")
    out.append("| ID | Category | Raw RAG | LLM Wiki |")
    out.append("|---|---|:---:|:---:|")
    for r in summary.rows:
        rag = "PASS" if r.rag_passed else "fail"
        wiki = "PASS" if r.wiki_passed else "fail"
        cat = r.category or "general"
        out.append(f"| {r.question_id} | {cat} | {rag} | {wiki} |")
    out.append("")

    out.append("## Failed checks detail\n")
    any_fail = False
    for r in summary.rows:
        if r.wiki_passed and r.rag_passed:
            continue
        any_fail = True
        out.append(f"### {r.question_id} — {r.question}\n")
        out.append(f"_category: {r.category}_\n")
        if not r.wiki_passed:
            out.append("**LLM Wiki failed checks:**")
            for c in r.wiki_checks:
                if not c.passed:
                    out.append(f"- {c.name}: {c.detail}")
            out.append("")
        if not r.rag_passed:
            out.append("**Raw RAG failed checks:**")
            for c in r.rag_checks:
                if not c.passed:
                    out.append(f"- {c.name}: {c.detail}")
            out.append("")
    if not any_fail:
        out.append("All questions passed for both providers.\n")

    return "\n".join(out)
