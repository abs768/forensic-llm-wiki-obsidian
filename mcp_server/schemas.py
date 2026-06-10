"""Pydantic I/O schemas for the MCP tools.

The schemas are deliberately small. The MCP layer is a thin wrapper over
``src/*`` — every output is JSON-serialisable and every input is a
plain dict with named fields.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------- #
# list_cases / get_case_summary / list_wiki_pages / read_wiki_page
# --------------------------------------------------------------------------- #


class CaseInfo(BaseModel):
    case_id: str
    has_wiki: bool
    has_raw_sources: bool


class ListCasesOutput(BaseModel):
    cases: list[CaseInfo] = Field(default_factory=list)


class GetCaseSummaryInput(BaseModel):
    case_id: str


class GetCaseSummaryOutput(BaseModel):
    case_id: str
    summary: str
    pages: list[str] = Field(default_factory=list)


class ListWikiPagesInput(BaseModel):
    case_id: str


class ListWikiPagesOutput(BaseModel):
    case_id: str
    pages: list[str] = Field(default_factory=list)


class ReadWikiPageInput(BaseModel):
    case_id: str
    page: str


class ReadWikiPageOutput(BaseModel):
    case_id: str
    page: str
    content: str


# --------------------------------------------------------------------------- #
# ingest_case_sources
# --------------------------------------------------------------------------- #


IngestMode = Literal["changed-only", "force", "apply"]


class IngestCaseSourcesInput(BaseModel):
    case_id: str
    mode: IngestMode = "changed-only"
    dry_run: bool = False
    review: bool = False


class IngestCaseSourcesOutput(BaseModel):
    case_id: str
    dry_run: bool
    review_mode: bool
    sources_processed: list[str] = Field(default_factory=list)
    sources_skipped: list[str] = Field(default_factory=list)
    pages_that_would_change: list[str] = Field(default_factory=list)
    pages_queued_for_review: list[str] = Field(default_factory=list)
    review_ids: list[str] = Field(default_factory=list)
    summary: str = ""


# --------------------------------------------------------------------------- #
# query_case / graph_query / compare_all_methods
# --------------------------------------------------------------------------- #


class QueryCaseInput(BaseModel):
    case_id: str
    question: str


class QueryCaseOutput(BaseModel):
    case_id: str
    question: str
    answer: str
    classification: str
    confidence: str
    assessment: str = ""
    evidence: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    insufficient: bool = False
    fell_back_to_raw_sources: bool = False


class GraphQueryInput(BaseModel):
    case_id: str
    question: str


class CompareAllMethodsInput(BaseModel):
    case_id: str
    question: str


class CompareAllMethodsOutput(BaseModel):
    case_id: str
    question: str
    raw_rag: str
    graph_rag_lite: str
    llm_wiki: str
    hybrid: str
    takeaway: str = (
        "Raw RAG retrieves snippets. GraphRAG-lite shows relationships. "
        "LLM Wiki gives current investigation assessment. "
        "Hybrid combines relationship structure with maintained case state."
    )


# --------------------------------------------------------------------------- #
# lint_case
# --------------------------------------------------------------------------- #


class LintIssue(BaseModel):
    severity: Literal["critical", "high", "medium", "low"]
    type: str
    location: str
    message: str


class LintCaseInput(BaseModel):
    case_id: str


class LintCaseOutput(BaseModel):
    case_id: str
    summary: dict[str, int] = Field(default_factory=dict)
    issues: list[LintIssue] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# generate_report
# --------------------------------------------------------------------------- #


class GenerateReportInput(BaseModel):
    case_id: str
    review: bool = False


class GenerateReportOutput(BaseModel):
    case_id: str
    report_path: str
    review_mode: bool = False
    held_for_review: bool = False
    review_id: str = ""
    summary: str = ""


# --------------------------------------------------------------------------- #
# get_hypothesis_history / get_contradictions / get_open_questions
# --------------------------------------------------------------------------- #


class GetHypothesisHistoryInput(BaseModel):
    case_id: str


class GetHypothesisHistoryOutput(BaseModel):
    case_id: str
    available: bool
    histories: list[dict] = Field(default_factory=list)


class GetContradictionsInput(BaseModel):
    case_id: str


class GetContradictionsOutput(BaseModel):
    case_id: str
    contradictions: list[dict] = Field(default_factory=list)
    contradictions_markdown: str = ""


class GetOpenQuestionsInput(BaseModel):
    case_id: str


class GetOpenQuestionsOutput(BaseModel):
    case_id: str
    questions: list[str] = Field(default_factory=list)
