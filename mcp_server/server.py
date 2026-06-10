"""MCP server entry point.

Runs the Forensic LLM Wiki tools over the MCP stdio transport so that
agent runtimes (Claude Desktop, mcp-cli, etc.) can call them.

Requires the optional ``mcp`` package — install with::

    pip install -e ".[dev,mcp]"

If the package is missing, importing this module raises a clear error.
The tools themselves live in :mod:`mcp_server.tools` and can be tested
without the MCP SDK installed at all.

Run with::

    python -m mcp_server.server
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - depends on env
    raise SystemExit(
        "The `mcp` package is required to run the MCP server. "
        "Install it with `pip install -e \".[dev,mcp]\"` and rerun."
    ) from exc

# Resolve project root from the repo layout (parent of this file's parent).
PROJECT_ROOT = Path(os.environ.get(
    "FORENSIC_WIKI_PROJECT_ROOT",
    str(Path(__file__).resolve().parents[1]),
))
sys.path.insert(0, str(PROJECT_ROOT))

from . import schemas as S  # noqa: E402
from . import tools as T  # noqa: E402

app = FastMCP("forensic-llm-wiki")


# --------------------------------------------------------------------------- #
# Tool registrations
#
# Each tool below is a thin wrapper that builds the Pydantic input model
# from the named MCP arguments and returns a JSON-serialisable dict.
# --------------------------------------------------------------------------- #


@app.tool()
def list_cases() -> dict:
    """List every case visible in raw_sources/ and wiki/cases/."""
    return T.list_cases(PROJECT_ROOT).model_dump()


@app.tool()
def get_case_summary(case_id: str) -> dict:
    """Return the contents of <case>/index.md and the list of available pages."""
    return T.get_case_summary(PROJECT_ROOT, S.GetCaseSummaryInput(case_id=case_id)).model_dump()


@app.tool()
def list_wiki_pages(case_id: str) -> dict:
    """List the markdown pages available for a case."""
    return T.list_wiki_pages(PROJECT_ROOT, S.ListWikiPagesInput(case_id=case_id)).model_dump()


@app.tool()
def read_wiki_page(case_id: str, page: str) -> dict:
    """Read a single wiki page. Refuses path traversal; sidecar is off-limits."""
    return T.read_wiki_page(
        PROJECT_ROOT, S.ReadWikiPageInput(case_id=case_id, page=page),
    ).model_dump()


@app.tool()
def ingest_case_sources(
    case_id: str, mode: str = "changed-only", dry_run: bool = False, review: bool = False,
) -> dict:
    """Compile raw_sources/<case> into the wiki. mode in {changed-only, force, apply}."""
    return T.ingest_case_sources(PROJECT_ROOT, S.IngestCaseSourcesInput(
        case_id=case_id, mode=mode, dry_run=dry_run, review=review,  # type: ignore[arg-type]
    )).model_dump()


@app.tool()
def query_case(case_id: str, question: str) -> dict:
    """Answer using the compiled LLM Wiki state. Falls back to raw lexical search if empty."""
    return T.query_case(
        PROJECT_ROOT, S.QueryCaseInput(case_id=case_id, question=question),
    ).model_dump()


@app.tool()
def lint_case(case_id: str) -> dict:
    """Run the wiki linter and return structured findings."""
    return T.lint_case(PROJECT_ROOT, S.LintCaseInput(case_id=case_id)).model_dump()


@app.tool()
def generate_report(case_id: str, review: bool = False) -> dict:
    """Generate or refresh final_report.md. In review mode, risky reports are queued."""
    return T.generate_report_tool(
        PROJECT_ROOT, S.GenerateReportInput(case_id=case_id, review=review),
    ).model_dump()


@app.tool()
def compare_all_methods(case_id: str, question: str) -> dict:
    """Run raw RAG, GraphRAG-lite, LLM Wiki, and Hybrid against the same question."""
    return T.compare_all_methods(
        PROJECT_ROOT, S.CompareAllMethodsInput(case_id=case_id, question=question),
    ).model_dump()


@app.tool()
def get_hypothesis_history(case_id: str) -> dict:
    """Return the per-step confidence trajectory for every tracked hypothesis."""
    return T.get_hypothesis_history(
        PROJECT_ROOT, S.GetHypothesisHistoryInput(case_id=case_id),
    ).model_dump()


@app.tool()
def get_contradictions(case_id: str) -> dict:
    """Return the contradictions.md text and the structured contradicting evidence."""
    return T.get_contradictions(
        PROJECT_ROOT, S.GetContradictionsInput(case_id=case_id),
    ).model_dump()


@app.tool()
def get_open_questions(case_id: str) -> dict:
    """Return the list of open investigation questions for the case."""
    return T.get_open_questions(
        PROJECT_ROOT, S.GetOpenQuestionsInput(case_id=case_id),
    ).model_dump()


@app.tool()
def graph_query(case_id: str, question: str) -> dict:
    """Answer a relationship question using the GraphRAG-lite graph."""
    return T.graph_query(
        PROJECT_ROOT, S.GraphQueryInput(case_id=case_id, question=question),
    ).model_dump()


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def main() -> None:
    app.run()


if __name__ == "__main__":
    main()
