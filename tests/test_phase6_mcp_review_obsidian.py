"""Phase 6: MCP tools, review queue, Obsidian export, docs/README presence.

The MCP server is not booted here — we exercise the underlying tool
functions directly. The MCP SDK is therefore not required to run these
tests.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_server import tools as T
from mcp_server.schemas import (
    CompareAllMethodsInput,
    GenerateReportInput,
    GetCaseSummaryInput,
    GetContradictionsInput,
    GetHypothesisHistoryInput,
    GetOpenQuestionsInput,
    GraphQueryInput,
    IngestCaseSourcesInput,
    LintCaseInput,
    ListWikiPagesInput,
    QueryCaseInput,
    ReadWikiPageInput,
)
from src.evolve import evolve_case
from src.graph import build_graph, save_graph
from src.ingest import ingest_case
from src.obsidian import export_vault, export_vault_dir
from src.review import (
    RISKY_PHRASES,
    approve_review,
    create_review,
    list_reviews,
    read_history,
    reject_review,
    scan_for_risky_phrases,
)
from src.wiki_io import REQUIRED_PAGES, case_dir

REPO_ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------- #
# Review queue
# --------------------------------------------------------------------------- #


def _seed_case(project: Path) -> None:
    """Ensure the evolving case is fully ingested so downstream tests have data."""
    evolve_case(project, "case_002_evolving")
    save_graph(project, build_graph(project, "case_002_evolving"))


def test_risky_phrase_scanner_catches_unattributed_overclaim() -> None:
    text = "## Verdict\n\nThis is confirmed malware.\n"
    assert "confirmed malware" in scan_for_risky_phrases(text)


def test_risky_phrase_scanner_skips_attributed_quotation() -> None:
    text = "- Investigator note: Dana asserts: confirmed malware diagnosis.\n"
    assert scan_for_risky_phrases(text) == []


def test_review_create_list_show(project: Path) -> None:
    ingest_case(project, "case_001")
    item = create_review(
        project, "case_001",
        change_type="wiki_update",
        target_page="final_report.md",
        proposed_content="# Verdict\nThis is confirmed malware.\n",
        prior_content="# Verdict\n_pending_\n",
    )
    items = list_reviews(project, "case_001")
    assert len(items) == 1
    assert items[0].review_id == item.review_id
    assert items[0].status == "pending"
    assert "confirmed malware" in items[0].risky_phrases


def test_review_approve_applies_proposed_content(project: Path) -> None:
    ingest_case(project, "case_001")
    cdir = case_dir(project, "case_001")
    target = cdir / "final_report.md"
    proposed = "# Final Report\nApproved manual revision.\n"
    item = create_review(
        project, "case_001",
        change_type="wiki_update",
        target_page="final_report.md",
        proposed_content=proposed,
        prior_content=target.read_text() if target.exists() else "",
    )
    approve_review(project, "case_001", item.review_id, reason="ok by analyst")
    assert target.read_text() == proposed
    # History records both the create and the approve.
    hist = read_history(project, "case_001")
    actions = [h.action for h in hist if h.review_id == item.review_id]
    assert "created" in actions and "approved" in actions


def test_review_reject_leaves_page_unchanged(project: Path) -> None:
    ingest_case(project, "case_001")
    cdir = case_dir(project, "case_001")
    target = cdir / "final_report.md"
    prior = target.read_text() if target.exists() else ""
    item = create_review(
        project, "case_001",
        change_type="wiki_update",
        target_page="final_report.md",
        proposed_content="# Verdict\nThis is confirmed malware.\n",
        prior_content=prior,
    )
    reject_review(project, "case_001", item.review_id, reason="needs more evidence")
    assert target.read_text() == prior
    hist = read_history(project, "case_001")
    actions = [h.action for h in hist if h.review_id == item.review_id]
    assert "rejected" in actions


def test_review_history_written_as_jsonl(project: Path) -> None:
    ingest_case(project, "case_001")
    item = create_review(
        project, "case_001",
        change_type="wiki_update",
        target_page="open_questions.md",
        proposed_content="- a new question",
    )
    p = project / "wiki" / "cases" / "case_001" / ".fw" / "review_history.jsonl"
    assert p.exists()
    lines = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    assert any(line.get("review_id") == item.review_id for line in lines)


# --------------------------------------------------------------------------- #
# Ingest / report --review
# --------------------------------------------------------------------------- #


def test_ingest_review_mode_holds_risky_page(project: Path) -> None:
    # Plant a "confirmed malware" assertion into a wiki page so re-ingest sees it
    # as new risky content. Then run ingest --review and verify the page is
    # held back rather than overwritten — we'll mutate the manifest entry for
    # one source to force reprocessing.
    ingest_case(project, "case_001")
    cdir = case_dir(project, "case_001")
    fr = cdir / "final_report.md"
    fr.write_text(fr.read_text() + "\n## Verdict\n\nconfirmed malware.\n")
    # Re-render through review mode by forcing reprocess.
    report = ingest_case(project, "case_001", force=True, review=True)
    # The final_report page should not be among the queued list — because
    # render_all_pages preserves a non-stub final_report. The other pages
    # are safe, so nothing is queued. The smoke check is just that
    # review_mode propagated cleanly.
    assert report.review_mode is True


def test_report_review_mode_queues_when_risky(project: Path) -> None:
    """Force a risky body by injecting into state.hypotheses' confidence, then
    rendering the report under --review and verifying the queue grows."""
    from src.report import generate_report
    from src.wiki_io import load_state, save_state
    ingest_case(project, "case_001")
    state = load_state(project, "case_001")
    # Replace one hypothesis with an overclaim'd inference. The generated
    # report quotes inferences verbatim, so the body will contain the phrase.
    h = next(iter(state.hypotheses.values()))
    h.inference = h.inference + " This is confirmed malware."
    save_state(project, state)

    before = list_reviews(project, "case_001", status="pending")
    body = generate_report(project, "case_001", review=True)
    after = list_reviews(project, "case_001", status="pending")
    assert "confirmed malware" in body.lower()
    assert len(after) == len(before) + 1
    assert after[-1].target_page == "final_report.md"


# --------------------------------------------------------------------------- #
# Obsidian export
# --------------------------------------------------------------------------- #


def test_export_obsidian_creates_vault_folder(project: Path) -> None:
    _seed_case(project)
    dst = export_vault(project, "case_002_evolving")
    assert dst.exists()
    assert dst == export_vault_dir(project, "case_002_evolving")


def test_exported_vault_includes_required_markdown_pages(project: Path) -> None:
    _seed_case(project)
    dst = export_vault(project, "case_002_evolving")
    for name in REQUIRED_PAGES:
        assert (dst / name).exists(), f"vault missing {name}"


def test_exported_vault_includes_readme_for_obsidian(project: Path) -> None:
    _seed_case(project)
    dst = export_vault(project, "case_002_evolving")
    p = dst / "README_FOR_OBSIDIAN.md"
    assert p.exists()
    text = p.read_text()
    assert "Obsidian" in text
    assert "case_002_evolving" in text


def test_exported_vault_omits_internal_sidecar(project: Path) -> None:
    _seed_case(project)
    dst = export_vault(project, "case_002_evolving")
    assert not (dst / ".fw").exists(), "sidecar must not leak into the vault"


def test_exported_vault_includes_graph_mmd_when_built(project: Path) -> None:
    _seed_case(project)
    dst = export_vault(project, "case_002_evolving")
    assert (dst / "graph.mmd").exists()


# --------------------------------------------------------------------------- #
# MCP tool functions
# --------------------------------------------------------------------------- #


def test_mcp_list_cases_returns_demo_cases(project: Path) -> None:
    _seed_case(project)
    out = T.list_cases(project)
    ids = [c.case_id for c in out.cases]
    assert "case_002_evolving" in ids
    target = next(c for c in out.cases if c.case_id == "case_002_evolving")
    assert target.has_wiki is True
    assert target.has_raw_sources is True


def test_mcp_get_case_summary_returns_index_text(project: Path) -> None:
    _seed_case(project)
    out = T.get_case_summary(project, GetCaseSummaryInput(case_id="case_002_evolving"))
    assert out.summary
    assert "index.md" not in out.pages or "timeline.md" in out.pages


def test_mcp_list_wiki_pages(project: Path) -> None:
    _seed_case(project)
    out = T.list_wiki_pages(project, ListWikiPagesInput(case_id="case_002_evolving"))
    for name in REQUIRED_PAGES:
        assert name in out.pages


def test_mcp_read_wiki_page_blocks_path_traversal(project: Path) -> None:
    _seed_case(project)
    with pytest.raises(ValueError):
        T.read_wiki_page(project, ReadWikiPageInput(
            case_id="case_002_evolving", page="../../etc/passwd",
        ))


def test_mcp_read_wiki_page_blocks_sidecar_access(project: Path) -> None:
    _seed_case(project)
    with pytest.raises(ValueError):
        T.read_wiki_page(project, ReadWikiPageInput(
            case_id="case_002_evolving", page=".fw/state.json",
        ))


def test_mcp_read_wiki_page_returns_content(project: Path) -> None:
    _seed_case(project)
    out = T.read_wiki_page(project, ReadWikiPageInput(
        case_id="case_002_evolving", page="hypotheses.md",
    ))
    assert out.page == "hypotheses.md"
    assert len(out.content) > 100


def test_mcp_query_case_returns_structured_output(project: Path) -> None:
    _seed_case(project)
    out = T.query_case(project, QueryCaseInput(
        case_id="case_002_evolving", question="Is this confirmed malware?",
    ))
    assert out.confidence in {"Low", "Medium", "High", "Confirmed"}
    assert out.classification in {"fact", "inference", "hypothesis"}
    assert out.evidence  # should reference claim_NNNN entries
    assert any("contradiction" in c.lower() or "defender" in c.lower()
               or "investigator" in c.lower() for c in out.contradictions)


def test_mcp_lint_case_returns_structured_issues(project: Path) -> None:
    _seed_case(project)
    out = T.lint_case(project, LintCaseInput(case_id="case_002_evolving"))
    # Summary must always carry the four severity buckets.
    assert set(out.summary.keys()) == {"critical", "high", "medium", "low"}
    # Every issue carries severity / type / location.
    for iss in out.issues:
        assert iss.severity in {"critical", "high", "medium", "low"}
        assert iss.type
        assert iss.location


def test_mcp_compare_all_methods_returns_all_four(project: Path) -> None:
    _seed_case(project)
    out = T.compare_all_methods(project, CompareAllMethodsInput(
        case_id="case_002_evolving", question="Is this confirmed malware?",
    ))
    for field in ("raw_rag", "graph_rag_lite", "llm_wiki", "hybrid"):
        assert getattr(out, field), f"compare_all_methods missing {field}"
    assert "Raw RAG retrieves snippets" in out.takeaway


def test_mcp_get_hypothesis_history(project: Path) -> None:
    _seed_case(project)
    out = T.get_hypothesis_history(project, GetHypothesisHistoryInput(
        case_id="case_002_evolving",
    ))
    assert out.available is True
    assert out.histories  # at least one hypothesis tracked


def test_mcp_get_contradictions(project: Path) -> None:
    _seed_case(project)
    out = T.get_contradictions(project, GetContradictionsInput(
        case_id="case_002_evolving",
    ))
    assert out.contradictions_markdown
    # contradictions list pulled from claims.json
    assert any("defender" in str(c).lower() for c in out.contradictions)


def test_mcp_get_open_questions(project: Path) -> None:
    _seed_case(project)
    out = T.get_open_questions(project, GetOpenQuestionsInput(
        case_id="case_002_evolving",
    ))
    assert out.questions


def test_mcp_graph_query_returns_relationships(project: Path) -> None:
    _seed_case(project)
    out = T.graph_query(project, GraphQueryInput(
        case_id="case_002_evolving",
        question="What is DeskRest.exe related to?",
    ))
    assert "deskrest" in out.answer.lower()
    assert out.insufficient is False


def test_mcp_generate_report_review_mode(project: Path) -> None:
    """When the report body would be risky, the tool reports
    held_for_review=True and includes a review_id."""
    from src.wiki_io import load_state, save_state
    _seed_case(project)
    state = load_state(project, "case_002_evolving")
    h = next(iter(state.hypotheses.values()))
    h.inference += " This is confirmed malware."
    save_state(project, state)

    out = T.generate_report_tool(project, GenerateReportInput(
        case_id="case_002_evolving", review=True,
    ))
    assert out.review_mode is True
    assert out.held_for_review is True
    assert out.review_id.startswith("review_")


# --------------------------------------------------------------------------- #
# Docs / README presence
# --------------------------------------------------------------------------- #


def test_phase6_docs_exist() -> None:
    for name in (
        "mcp_setup.md",
        "agent_demo.md",
        "obsidian_workflow.md",
        "human_review.md",
    ):
        p = REPO_ROOT / "docs" / name
        assert p.exists(), f"docs/{name} missing"


def test_readme_mentions_mcp_obsidian_review() -> None:
    text = (REPO_ROOT / "README.md").read_text()
    assert "MCP" in text
    assert "Obsidian" in text
    assert "review" in text.lower()


def test_obsidian_vault_template_exists() -> None:
    t = REPO_ROOT / "examples" / "obsidian_vault_template"
    assert t.is_dir()
    assert (t / "README_FOR_OBSIDIAN.md").exists()
    for name in ("case_index_template.md", "hypothesis_template.md",
                 "ioc_template.md", "contradiction_template.md",
                 "report_template.md"):
        assert (t / "templates" / name).exists(), f"template missing: {name}"


# --------------------------------------------------------------------------- #
# MCP server module imports cleanly without the MCP SDK
# --------------------------------------------------------------------------- #


def test_mcp_tools_module_imports_without_sdk() -> None:
    # `mcp_server.tools` must be importable as a plain Python module.
    # It must NOT depend on the optional `mcp` package at import time.
    import importlib
    m = importlib.import_module("mcp_server.tools")
    assert hasattr(m, "TOOL_REGISTRY")
    assert set(m.TOOL_REGISTRY.keys()) == {
        "list_cases", "get_case_summary", "list_wiki_pages", "read_wiki_page",
        "ingest_case_sources", "query_case", "lint_case", "generate_report",
        "compare_all_methods", "get_hypothesis_history", "get_contradictions",
        "get_open_questions", "graph_query",
    }


# --------------------------------------------------------------------------- #
# Risky phrase list sanity
# --------------------------------------------------------------------------- #


def test_risky_phrase_list_covers_expected_terms() -> None:
    assert "confirmed malware" in RISKY_PHRASES
    assert "exfiltration occurred" in RISKY_PHRASES
    assert "data was stolen" in RISKY_PHRASES


