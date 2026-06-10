"""MCP tool implementations.

Every function here:

  - takes a Pydantic input model (or named args),
  - returns a Pydantic output model,
  - calls existing ``src/*`` services — no duplicate core logic,
  - is safe to call from tests without any MCP runtime installed.

Path-traversal protection lives in :func:`_resolve_inside_case` and is
used by :func:`read_wiki_page`.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.benchmark_methods import benchmark_methods  # noqa: F401 (used indirectly)
from src.compare_all import compare_all
from src.graph import build_graph, save_graph
from src.graph.graph_builder import graph_path
from src.graph.graph_query import graph_query as graph_query_impl
from src.hypothesis_history import history_path, load_history
from src.ingest import ingest_case
from src.lint import lint_case as lint_case_impl
from src.llm import LLMClient
from src.query import answer_question, format_answer
from src.report import generate_report
from src.review import list_reviews
from src.wiki_io import REQUIRED_PAGES, case_dir, wiki_root

from .schemas import (
    CaseInfo,
    CompareAllMethodsInput,
    CompareAllMethodsOutput,
    GenerateReportInput,
    GenerateReportOutput,
    GetCaseSummaryInput,
    GetCaseSummaryOutput,
    GetContradictionsInput,
    GetContradictionsOutput,
    GetHypothesisHistoryInput,
    GetHypothesisHistoryOutput,
    GetOpenQuestionsInput,
    GetOpenQuestionsOutput,
    GraphQueryInput,
    IngestCaseSourcesInput,
    IngestCaseSourcesOutput,
    LintCaseInput,
    LintCaseOutput,
    LintIssue,
    ListCasesOutput,
    ListWikiPagesInput,
    ListWikiPagesOutput,
    QueryCaseInput,
    QueryCaseOutput,
    ReadWikiPageInput,
    ReadWikiPageOutput,
)

# --------------------------------------------------------------------------- #
# Path-safety helper
# --------------------------------------------------------------------------- #


def _resolve_inside_case(project_root: Path, case_id: str, relative: str) -> Path:
    """Resolve ``relative`` against the case wiki dir, refusing traversal.

    Raises ``ValueError`` for any path that escapes the case wiki dir
    (absolute paths, ``..``-walks, paths starting with ``.``).
    """
    if not case_id or "/" in case_id or "\\" in case_id or case_id.startswith("."):
        raise ValueError(f"Invalid case_id: {case_id!r}")
    if not relative or relative.startswith("/") or relative.startswith("\\"):
        raise ValueError(f"Invalid page path: {relative!r}")
    if ".." in Path(relative).parts:
        raise ValueError(f"Path traversal denied: {relative!r}")
    cdir = case_dir(project_root, case_id).resolve()
    target = (cdir / relative).resolve()
    try:
        target.relative_to(cdir)
    except ValueError as exc:
        raise ValueError(f"Path escapes case wiki dir: {relative!r}") from exc
    # Block the sidecar: agents should not pull state.json via this tool.
    if ".fw" in target.relative_to(cdir).parts:
        raise ValueError(f"Sidecar directory is off-limits: {relative!r}")
    return target


# --------------------------------------------------------------------------- #
# 1. list_cases
# --------------------------------------------------------------------------- #


def list_cases(project_root: Path) -> ListCasesOutput:
    cases: dict[str, CaseInfo] = {}
    raw_root = project_root / "raw_sources"
    if raw_root.exists():
        for p in sorted(raw_root.iterdir()):
            if p.is_dir() and not p.name.startswith("."):
                cases[p.name] = CaseInfo(
                    case_id=p.name, has_wiki=False, has_raw_sources=True,
                )
    wiki_cases = wiki_root(project_root) / "cases"
    if wiki_cases.exists():
        for p in sorted(wiki_cases.iterdir()):
            if p.is_dir() and not p.name.startswith("."):
                if p.name in cases:
                    cases[p.name].has_wiki = True
                else:
                    cases[p.name] = CaseInfo(
                        case_id=p.name, has_wiki=True, has_raw_sources=False,
                    )
    return ListCasesOutput(cases=sorted(cases.values(), key=lambda c: c.case_id))


# --------------------------------------------------------------------------- #
# 2. get_case_summary
# --------------------------------------------------------------------------- #


def get_case_summary(project_root: Path, inp: GetCaseSummaryInput) -> GetCaseSummaryOutput:
    cdir = case_dir(project_root, inp.case_id)
    summary = ""
    pages: list[str] = []
    idx = cdir / "index.md"
    if idx.exists():
        summary = idx.read_text()
    for name in REQUIRED_PAGES:
        if (cdir / name).exists():
            pages.append(name)
    return GetCaseSummaryOutput(case_id=inp.case_id, summary=summary, pages=pages)


# --------------------------------------------------------------------------- #
# 3. list_wiki_pages
# --------------------------------------------------------------------------- #


def list_wiki_pages(project_root: Path, inp: ListWikiPagesInput) -> ListWikiPagesOutput:
    cdir = case_dir(project_root, inp.case_id)
    pages: list[str] = []
    if cdir.exists():
        for name in REQUIRED_PAGES:
            if (cdir / name).exists():
                pages.append(name)
        # Also surface graph.mmd if it's been built.
        if (cdir / ".fw" / "graph.mmd").exists():
            pages.append(".fw/graph.mmd")
    return ListWikiPagesOutput(case_id=inp.case_id, pages=pages)


# --------------------------------------------------------------------------- #
# 4. read_wiki_page  (with path-traversal protection)
# --------------------------------------------------------------------------- #


def read_wiki_page(project_root: Path, inp: ReadWikiPageInput) -> ReadWikiPageOutput:
    target = _resolve_inside_case(project_root, inp.case_id, inp.page)
    if not target.exists():
        raise FileNotFoundError(f"Wiki page not found: {inp.page}")
    return ReadWikiPageOutput(
        case_id=inp.case_id, page=inp.page, content=target.read_text(),
    )


# --------------------------------------------------------------------------- #
# 5. ingest_case_sources
# --------------------------------------------------------------------------- #


def ingest_case_sources(
    project_root: Path, inp: IngestCaseSourcesInput,
) -> IngestCaseSourcesOutput:
    force = inp.mode == "force"
    changed_only = inp.mode == "changed-only"
    report = ingest_case(
        project_root, inp.case_id,
        llm=LLMClient(mode="mock"),
        force=force,
        changed_only=changed_only,
        dry_run=inp.dry_run,
        review=inp.review,
    )
    return IngestCaseSourcesOutput(
        case_id=inp.case_id,
        dry_run=report.dry_run,
        review_mode=report.review_mode,
        sources_processed=report.sources_processed,
        sources_skipped=report.sources_skipped,
        pages_that_would_change=report.pages_changed,
        pages_queued_for_review=report.pages_queued_for_review,
        review_ids=report.review_ids,
        summary=(
            f"Processed {len(report.sources_processed)}, "
            f"skipped {len(report.sources_skipped)}, "
            f"pages changed {len(report.pages_changed)}"
            + (f", queued for review {len(report.pages_queued_for_review)}"
               if report.review_mode else "")
        ),
    )


# --------------------------------------------------------------------------- #
# 6. query_case
# --------------------------------------------------------------------------- #


def query_case(project_root: Path, inp: QueryCaseInput) -> QueryCaseOutput:
    ans = answer_question(project_root, inp.case_id, inp.question)
    return QueryCaseOutput(
        case_id=inp.case_id,
        question=inp.question,
        answer=ans.answer,
        classification=ans.classification,
        confidence=ans.confidence,
        assessment=ans.assessment,
        evidence=ans.evidence_items,
        contradictions=ans.contradicting_evidence,
        sources=ans.supporting_sources,
        insufficient=ans.insufficient,
        fell_back_to_raw_sources=ans.fell_back_to_raw_sources,
    )


# --------------------------------------------------------------------------- #
# 7. lint_case
# --------------------------------------------------------------------------- #


def lint_case(project_root: Path, inp: LintCaseInput) -> LintCaseOutput:
    report = lint_case_impl(project_root, inp.case_id)
    issues = [
        LintIssue(
            severity=f.severity.lower(),  # type: ignore[arg-type]
            type=f.rule,
            location=f.page,
            message=f.message,
        )
        for f in report.findings
    ]
    return LintCaseOutput(
        case_id=inp.case_id,
        summary=report.summary(),
        issues=issues,
    )


# --------------------------------------------------------------------------- #
# 8. generate_report
# --------------------------------------------------------------------------- #


def generate_report_tool(project_root: Path, inp: GenerateReportInput) -> GenerateReportOutput:
    pending_before = {r.review_id for r in list_reviews(project_root, inp.case_id, status="pending")}
    body = generate_report(project_root, inp.case_id, review=inp.review)
    pending_after = list_reviews(project_root, inp.case_id, status="pending")
    new_items = [r for r in pending_after if r.review_id not in pending_before
                 and r.target_page == "final_report.md"]
    held = bool(new_items)
    report_path = str((case_dir(project_root, inp.case_id) / "final_report.md")
                      .relative_to(project_root))
    return GenerateReportOutput(
        case_id=inp.case_id,
        report_path=report_path,
        review_mode=inp.review,
        held_for_review=held,
        review_id=new_items[0].review_id if held else "",
        summary=body[:300] + ("…" if len(body) > 300 else ""),
    )


# --------------------------------------------------------------------------- #
# 9. compare_all_methods
# --------------------------------------------------------------------------- #


def compare_all_methods(
    project_root: Path, inp: CompareAllMethodsInput,
) -> CompareAllMethodsOutput:
    # Ensure the graph exists so GraphRAG-lite has something to read.
    if not graph_path(project_root, inp.case_id).exists():
        save_graph(project_root, build_graph(project_root, inp.case_id))
    result = compare_all(project_root, inp.case_id, inp.question)
    return CompareAllMethodsOutput(
        case_id=inp.case_id,
        question=inp.question,
        raw_rag=format_answer(result.raw_rag),
        graph_rag_lite=format_answer(result.graph_rag_lite),
        llm_wiki=format_answer(result.llm_wiki),
        hybrid=format_answer(result.hybrid),
    )


# --------------------------------------------------------------------------- #
# 10. get_hypothesis_history
# --------------------------------------------------------------------------- #


def get_hypothesis_history(
    project_root: Path, inp: GetHypothesisHistoryInput,
) -> GetHypothesisHistoryOutput:
    p = history_path(project_root, inp.case_id)
    if not p.exists():
        return GetHypothesisHistoryOutput(
            case_id=inp.case_id, available=False, histories=[],
        )
    hist = load_history(project_root, inp.case_id)
    return GetHypothesisHistoryOutput(
        case_id=inp.case_id,
        available=True,
        histories=[h.model_dump() for h in hist.histories],
    )


# --------------------------------------------------------------------------- #
# 11. get_contradictions
# --------------------------------------------------------------------------- #


def get_contradictions(
    project_root: Path, inp: GetContradictionsInput,
) -> GetContradictionsOutput:
    cdir = case_dir(project_root, inp.case_id)
    md = ""
    md_path = cdir / "contradictions.md"
    if md_path.exists():
        md = md_path.read_text()
    cj = cdir / ".fw" / "claims.json"
    contras: list[dict] = []
    if cj.exists():
        for claim in json.loads(cj.read_text()):
            if claim.get("contradicting_evidence"):
                contras.append({
                    "claim_id": claim.get("claim_id"),
                    "claim_text": claim.get("claim_text"),
                    "contradicting_evidence": claim.get("contradicting_evidence"),
                })
    return GetContradictionsOutput(
        case_id=inp.case_id,
        contradictions=contras,
        contradictions_markdown=md,
    )


# --------------------------------------------------------------------------- #
# 12. get_open_questions
# --------------------------------------------------------------------------- #


def get_open_questions(
    project_root: Path, inp: GetOpenQuestionsInput,
) -> GetOpenQuestionsOutput:
    cdir = case_dir(project_root, inp.case_id)
    p = cdir / "open_questions.md"
    if not p.exists():
        return GetOpenQuestionsOutput(case_id=inp.case_id, questions=[])
    questions = []
    for line in p.read_text().splitlines():
        s = line.strip()
        # Bullet-style open-question line: "- [ ] ..." or "- ..."
        if s.startswith("- ["):
            q = s.split("]", 1)[-1].strip()
            if q:
                questions.append(q)
        elif s.startswith("- ") and len(s) > 2 and not s.startswith("- _"):
            questions.append(s[2:].strip())
    return GetOpenQuestionsOutput(case_id=inp.case_id, questions=questions)


# --------------------------------------------------------------------------- #
# 13. graph_query
# --------------------------------------------------------------------------- #


def graph_query(project_root: Path, inp: GraphQueryInput) -> QueryCaseOutput:
    # Build the graph on demand if it isn't there.
    if not graph_path(project_root, inp.case_id).exists():
        cdir = case_dir(project_root, inp.case_id)
        if (cdir / ".fw").exists():
            save_graph(project_root, build_graph(project_root, inp.case_id))
    ans = graph_query_impl(project_root, inp.case_id, inp.question)
    return QueryCaseOutput(
        case_id=inp.case_id,
        question=inp.question,
        answer=ans.answer,
        classification=ans.classification,
        confidence=ans.confidence,
        assessment=ans.assessment,
        evidence=ans.evidence_items,
        contradictions=ans.contradicting_evidence,
        sources=ans.supporting_sources,
        insufficient=ans.insufficient,
        fell_back_to_raw_sources=ans.fell_back_to_raw_sources,
    )


# --------------------------------------------------------------------------- #
# Convenience: tool name → callable, used by server.py
# --------------------------------------------------------------------------- #


TOOL_REGISTRY = {
    "list_cases":               list_cases,
    "get_case_summary":         get_case_summary,
    "list_wiki_pages":          list_wiki_pages,
    "read_wiki_page":           read_wiki_page,
    "ingest_case_sources":      ingest_case_sources,
    "query_case":               query_case,
    "lint_case":                lint_case,
    "generate_report":          generate_report_tool,
    "compare_all_methods":      compare_all_methods,
    "get_hypothesis_history":   get_hypothesis_history,
    "get_contradictions":       get_contradictions,
    "get_open_questions":       get_open_questions,
    "graph_query":              graph_query,
}
