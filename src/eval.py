"""Eval runner.

Reads ``evals/<case>_eval.json``, runs each question through the wiki
``query`` operation, and applies a fixed set of checks:

  - must_include          — every term must appear in the answer text
  - must_not_include      — none of the terms may appear
  - required_sources      — each filename must appear in the answer text
                            (matched on basename, so the eval doesn't have
                            to encode the full raw_sources/<case>/... prefix)
  - expect_refusal        — answer must contain "no", "not", or "insufficient"
                            (i.e. it must not assert a yes)
  - expect_separation     — answer must split facts from hypotheses, signalled
                            by mentions of both "fact" and "hypothesis"
                            (case-insensitive) or by classification=hypothesis

Failure categories tracked separately for the summary:

  - unsupported_claim_failures  — a must_not_include term appeared
  - missing_source_failures     — a required_source did not appear

Tests for the eval runner are in ``tests/test_eval.py``.
"""
from __future__ import annotations

import json
from pathlib import Path

from .query import answer_question, format_answer
from .schemas import EvalCase, EvalCaseResult, EvalCheck, EvalSummary


def load_eval_file(project_root: Path, case_id: str) -> list[EvalCase]:
    p = project_root / "evals" / f"{case_id}_eval.json"
    if not p.exists():
        return []
    payload = json.loads(p.read_text())
    items = payload.get("items", payload)  # accept either wrapped or bare list
    return [EvalCase.model_validate(x) for x in items]


def evaluate_answer(case: EvalCase, ans, text: str) -> tuple[EvalCaseResult, int, int]:
    """Score one answer against one eval case. Returns the result plus
    counts of unsupported_claim_failures and missing_source_failures for
    this single case (so the caller can aggregate across many cases or
    many answer-providers)."""
    checks: list[EvalCheck] = []
    unsupported = 0
    missing_sources = 0

    for term in case.must_include:
        ok = term.lower() in text.lower()
        checks.append(EvalCheck(
            name=f"must_include:{term}",
            passed=ok,
            detail="" if ok else f"missing term '{term}'",
        ))

    for term in case.must_not_include:
        ok = term.lower() not in text.lower()
        checks.append(EvalCheck(
            name=f"must_not_include:{term}",
            passed=ok,
            detail="" if ok else f"forbidden term '{term}' appeared",
        ))
        if not ok:
            unsupported += 1

    for src in case.required_sources:
        base = Path(src).name
        ok = base.lower() in text.lower()
        checks.append(EvalCheck(
            name=f"required_source:{base}",
            passed=ok,
            detail="" if ok else f"source '{base}' not mentioned",
        ))
        if not ok:
            missing_sources += 1

    if case.expect_refusal:
        text_lower = text.lower()
        ok = (
            getattr(ans, "insufficient", False)
            or "not confirmed" in text_lower
            or text_lower.lstrip().startswith("answer:\nno")
            or "\nno." in text_lower
            or "\nno " in text_lower
        )
        checks.append(EvalCheck(
            name="expect_refusal",
            passed=ok,
            detail="" if ok else "answer did not refuse the unsupported claim",
        ))

    if case.expect_separation:
        text_lower = text.lower()
        ok = (
            getattr(ans, "classification", "") == "hypothesis"
            or ("fact" in text_lower and "hypothesis" in text_lower)
        )
        checks.append(EvalCheck(
            name="expect_separation",
            passed=ok,
            detail="" if ok else "answer did not separate facts from hypotheses",
        ))

    passed = all(c.passed for c in checks)
    return (
        EvalCaseResult(
            id=case.id,
            question=case.question,
            passed=passed,
            checks=checks,
            answer_text=text,
        ),
        unsupported,
        missing_sources,
    )


def run_eval(project_root: Path, case_id: str) -> EvalSummary:
    cases = load_eval_file(project_root, case_id)
    results: list[EvalCaseResult] = []
    unsupported = 0
    missing_sources = 0

    for case in cases:
        ans = answer_question(project_root, case_id, case.question)
        text = format_answer(ans)
        result, u, m = evaluate_answer(case, ans, text)
        results.append(result)
        unsupported += u
        missing_sources += m

    return EvalSummary(
        total=len(results),
        passed=sum(1 for r in results if r.passed),
        failed=sum(1 for r in results if not r.passed),
        unsupported_claim_failures=unsupported,
        missing_source_failures=missing_sources,
        results=results,
    )


def format_summary(summary: EvalSummary, *, verbose: bool = False) -> str:
    lines: list[str] = []
    lines.append("Eval summary:")
    lines.append(f"Total: {summary.total}")
    lines.append(f"Passed: {summary.passed}")
    lines.append(f"Failed: {summary.failed}")
    lines.append(f"Unsupported claim failures: {summary.unsupported_claim_failures}")
    lines.append(f"Missing source failures: {summary.missing_source_failures}")
    if not verbose and summary.failed == 0:
        return "\n".join(lines)
    lines.append("")
    for r in summary.results:
        status = "PASS" if r.passed else "FAIL"
        lines.append(f"[{status}] {r.id}: {r.question}")
        if r.passed and not verbose:
            continue
        for c in r.checks:
            mark = "ok" if c.passed else "FAIL"
            detail = f" — {c.detail}" if c.detail else ""
            lines.append(f"    [{mark}] {c.name}{detail}")
    return "\n".join(lines)
