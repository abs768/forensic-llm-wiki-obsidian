#!/usr/bin/env python3
"""Forensic LLM Wiki CLI.

Phase 1 operations:
    python fw.py ingest raw_sources/case_001
    python fw.py query  case_001 "Is this confirmed malware?"
    python fw.py lint   case_001
    python fw.py report case_001

Phase 2 additions:
    python fw.py ingest raw_sources/case_001 --dry-run
    python fw.py ingest raw_sources/case_001 --apply
    python fw.py ingest raw_sources/case_001 --changed-only
    python fw.py ingest raw_sources/case_001 --force
    python fw.py lint   case_001 --json
    python fw.py rag-query case_001 "Is this confirmed malware?"
    python fw.py compare   case_001 "Is this confirmed malware?"
    python fw.py eval      case_001
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.benchmark import benchmark_case  # noqa: E402
from src.benchmark import format_markdown as format_benchmark_md  # noqa: E402
from src.benchmark_methods import benchmark_methods, format_method_markdown  # noqa: E402
from src.compare import compare, format_comparison  # noqa: E402
from src.compare_all import compare_all, format_four_way  # noqa: E402
from src.eval import format_summary, run_eval  # noqa: E402
from src.evolve import benchmark_case_dir, evolve_case  # noqa: E402
from src.graph import build_graph, graph_md_path, graph_query, save_graph, to_mermaid  # noqa: E402
from src.graph.graph_builder import graph_mmd_path, graph_path  # noqa: E402
from src.ingest import format_dry_run, ingest_case  # noqa: E402
from src.lint import format_json as format_lint_json  # noqa: E402
from src.lint import format_report as format_lint_report  # noqa: E402
from src.lint import lint_case  # noqa: E402
from src.llm import LLMClient  # noqa: E402
from src.manifest import load_manifest, mark_lint_run, save_manifest  # noqa: E402
from src.obsidian import export_vault  # noqa: E402
from src.query import answer_question, format_answer  # noqa: E402
from src.rag import rag_query  # noqa: E402
from src.report import generate_report  # noqa: E402
from src.review import approve_review, list_reviews, load_review, reject_review  # noqa: E402
from src.review import format_list as format_review_list  # noqa: E402
from src.review import format_show as format_review_show  # noqa: E402
from src.snapshots import diff_snapshots, format_diff  # noqa: E402


def _case_id_from_arg(arg: str) -> str:
    """Accept both 'case_001' and 'raw_sources/case_001' for convenience."""
    p = Path(arg)
    if p.name == "":
        return p.parent.name
    return p.name


def cmd_ingest(args: argparse.Namespace) -> int:
    case_id = _case_id_from_arg(args.case)
    mode = "live" if args.live else "mock"
    report = ingest_case(
        PROJECT_ROOT,
        case_id,
        llm=LLMClient(mode=mode),
        force=args.force,
        changed_only=args.changed_only,
        dry_run=args.dry_run,
        review=args.review,
    )
    if args.dry_run:
        print(format_dry_run(report))
        return 0
    print(f"Ingested case '{case_id}' (mode={mode}).")
    print(f"  Processed: {len(report.sources_processed)} file(s)")
    for s in report.sources_processed:
        print(f"    + {s}")
    if report.sources_skipped:
        print(f"  Skipped (unchanged): {len(report.sources_skipped)} file(s)")
        for s in report.sources_skipped:
            print(f"    = {s}")
    print(f"  Wrote {len(report.pages_written)} wiki page(s); "
          f"{len(report.pages_changed)} actually changed.")
    if report.pages_queued_for_review:
        print(f"  Held for review: {len(report.pages_queued_for_review)} page(s)")
        for name, rid in zip(report.pages_queued_for_review, report.review_ids, strict=False):
            print(f"    ? {name}  →  {rid}  (fw.py review show {case_id} {rid})")
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    case_id = _case_id_from_arg(args.case)
    ans = answer_question(PROJECT_ROOT, case_id, args.question)
    print(format_answer(ans))
    return 0


def cmd_rag_query(args: argparse.Namespace) -> int:
    case_id = _case_id_from_arg(args.case)
    ans = rag_query(PROJECT_ROOT, case_id, args.question)
    print(format_answer(ans))
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    case_id = _case_id_from_arg(args.case)
    result = compare(PROJECT_ROOT, case_id, args.question)
    print(format_comparison(result))
    return 0


def cmd_lint(args: argparse.Namespace) -> int:
    case_id = _case_id_from_arg(args.case)
    report = lint_case(PROJECT_ROOT, case_id)
    # Stamp the manifest so stale-page checks have a reference time.
    manifest = load_manifest(PROJECT_ROOT, case_id)
    if manifest.case_id:
        mark_lint_run(manifest)
        save_manifest(PROJECT_ROOT, manifest)
    if args.json:
        print(format_lint_json(report))
    else:
        print(format_lint_report(report))
    if report.by_severity("Critical") or report.by_severity("High"):
        return 1
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    case_id = _case_id_from_arg(args.case)
    pending_before = {r.review_id for r in list_reviews(PROJECT_ROOT, case_id, status="pending")}
    body = generate_report(PROJECT_ROOT, case_id, review=args.review)
    print(body)
    if args.review:
        pending_after = list_reviews(PROJECT_ROOT, case_id, status="pending")
        new_items = [r for r in pending_after if r.review_id not in pending_before]
        if new_items:
            print()
            for item in new_items:
                print(
                    f"# Held for review: {item.review_id} ({item.target_page}). "
                    f"Run `fw.py review approve {case_id} {item.review_id}` to apply."
                )
        else:
            print()
            print("# No risky phrases detected; final_report.md updated.")
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    case_id = _case_id_from_arg(args.case)
    summary = run_eval(PROJECT_ROOT, case_id)
    print(format_summary(summary, verbose=args.verbose))
    return 0 if summary.failed == 0 else 1


def cmd_evolve(args: argparse.Namespace) -> int:
    case_id = _case_id_from_arg(args.case)
    result = evolve_case(
        PROJECT_ROOT,
        case_id,
        llm=LLMClient(mode="live" if args.live else "mock"),
        key_question=args.key_question,
        fresh=not args.resume,
    )
    print(f"Evolved case '{case_id}' across {len(result.steps)} step(s).")
    for step in result.steps:
        passed = step.eval_summary.passed if step.eval_summary else "-"
        total = step.eval_summary.total if step.eval_summary else "-"
        ls = step.lint_summary
        print(
            f"  {step.name}: +{len(step.files_added)} files, "
            f"{len(step.pages_changed)} pages changed, "
            f"{len(step.new_hypotheses)} new hyp, "
            f"{len(step.new_contradictions)} new contradictions, "
            f"lint(c={ls.get('critical', 0)}/h={ls.get('high', 0)}/m={ls.get('medium', 0)}/l={ls.get('low', 0)}), "
            f"eval {passed}/{total}"
        )
    report = benchmark_case_dir(PROJECT_ROOT, case_id) / "evolution_report.md"
    print(f"Evolution report: {report.relative_to(PROJECT_ROOT)}")
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    case_id = _case_id_from_arg(args.case)
    summary = benchmark_case(PROJECT_ROOT, case_id)
    if args.json:
        print(summary.model_dump_json(indent=2))
    else:
        print(format_benchmark_md(summary))
    out = benchmark_case_dir(PROJECT_ROOT, case_id)
    print(f"\nWrote: {(out / 'results.md').relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {(out / 'results.json').relative_to(PROJECT_ROOT)}")
    return 0


def cmd_diff_snapshots(args: argparse.Namespace) -> int:
    case_id = _case_id_from_arg(args.case)
    diffs = diff_snapshots(PROJECT_ROOT, case_id, args.snapshot_a, args.snapshot_b)
    print(format_diff(case_id, args.snapshot_a, args.snapshot_b, diffs))
    return 0


def cmd_graph_build(args: argparse.Namespace) -> int:
    case_id = _case_id_from_arg(args.case)
    graph = build_graph(PROJECT_ROOT, case_id)
    paths = save_graph(PROJECT_ROOT, graph)
    print(f"Built relationship graph for '{case_id}'.")
    print(f"  Nodes: {len(graph.nodes)}, edges: {len(graph.edges)}")
    for _name, p in paths.items():
        print(f"  Wrote: {p.relative_to(PROJECT_ROOT)}")
    return 0


def cmd_graph_query(args: argparse.Namespace) -> int:
    case_id = _case_id_from_arg(args.case)
    ans = graph_query(PROJECT_ROOT, case_id, args.question)
    print(format_answer(ans))
    return 0


def cmd_graph_export(args: argparse.Namespace) -> int:
    case_id = _case_id_from_arg(args.case)
    graph = build_graph(PROJECT_ROOT, case_id)
    if args.format == "mermaid":
        text = to_mermaid(graph)
        out = graph_mmd_path(PROJECT_ROOT, case_id)
    elif args.format == "json":
        text = graph.model_dump_json(indent=2)
        out = graph_path(PROJECT_ROOT, case_id)
    elif args.format == "md":
        save_graph(PROJECT_ROOT, graph)  # also rewrites markdown
        out = graph_md_path(PROJECT_ROOT, case_id)
        text = out.read_text()
    else:  # pragma: no cover - argparse limits the choices
        raise ValueError(f"Unknown format: {args.format}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(text)
    print(f"\nWrote: {out.relative_to(PROJECT_ROOT)}")
    return 0


def cmd_compare_all(args: argparse.Namespace) -> int:
    case_id = _case_id_from_arg(args.case)
    # Ensure the graph exists so GraphRAG-lite has something to read.
    if not graph_path(PROJECT_ROOT, case_id).exists():
        graph = build_graph(PROJECT_ROOT, case_id)
        save_graph(PROJECT_ROOT, graph)
    result = compare_all(PROJECT_ROOT, case_id, args.question)
    print(format_four_way(result))
    return 0


def cmd_export_obsidian(args: argparse.Namespace) -> int:
    case_id = _case_id_from_arg(args.case)
    dst = export_vault(PROJECT_ROOT, case_id)
    print(f"Exported Obsidian vault for '{case_id}' to:")
    print(f"  {dst.relative_to(PROJECT_ROOT)}")
    print("Open that folder in Obsidian (File → Open vault → Open folder as vault).")
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    case_id = _case_id_from_arg(args.case)
    if args.review_action == "list":
        items = list_reviews(PROJECT_ROOT, case_id, status=args.status)
        print(format_review_list(items))
        return 0
    if args.review_action == "show":
        item = load_review(PROJECT_ROOT, case_id, args.review_id)
        print(format_review_show(item))
        return 0
    if args.review_action == "approve":
        item = approve_review(PROJECT_ROOT, case_id, args.review_id, reason=args.reason or "")
        print(f"Approved {item.review_id} → applied to {item.target_page}.")
        return 0
    if args.review_action == "reject":
        item = reject_review(PROJECT_ROOT, case_id, args.review_id, reason=args.reason or "")
        print(f"Rejected {item.review_id} (target page {item.target_page} unchanged).")
        return 0
    raise ValueError(f"Unknown review action: {args.review_action}")


def cmd_benchmark_methods(args: argparse.Namespace) -> int:
    case_id = _case_id_from_arg(args.case)
    if not graph_path(PROJECT_ROOT, case_id).exists():
        graph = build_graph(PROJECT_ROOT, case_id)
        save_graph(PROJECT_ROOT, graph)
    summary = benchmark_methods(PROJECT_ROOT, case_id)
    if args.json:
        print(summary.model_dump_json(indent=2))
    else:
        print(format_method_markdown(summary))
    out = benchmark_case_dir(PROJECT_ROOT, case_id)
    print(f"\nWrote: {(out / 'method_comparison.md').relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {(out / 'method_comparison.json').relative_to(PROJECT_ROOT)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fw",
        description=(
            "Forensic LLM Wiki — compile forensic evidence into an evolving, "
            "citation-backed markdown investigation wiki. Not a generic RAG "
            "chatbot."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Common workflows:\n"
            "  fw.py ingest raw_sources/case_001 --dry-run\n"
            "  fw.py ingest raw_sources/case_001 --apply\n"
            "  fw.py query case_001 \"Is this confirmed malware?\"\n"
            "  fw.py compare case_001 \"Is this confirmed malware?\"\n"
            "  fw.py evolve case_002_evolving\n"
            "  fw.py benchmark case_002_evolving\n"
        ),
    )
    sub = parser.add_subparsers(
        dest="op",
        required=True,
        title="commands",
        metavar="<command>",
    )

    p_ing = sub.add_parser(
        "ingest",
        help="Compile raw evidence into the markdown wiki.",
        description=(
            "Walk raw_sources/<case>/ recursively, extract structured facts, "
            "and update the compiled wiki. Skips unchanged files by default; "
            "use --force to reprocess everything, --dry-run to preview diffs."
        ),
    )
    p_ing.add_argument("case", help="raw_sources/<case_id> or <case_id>")
    p_ing.add_argument("--live", action="store_true",
                       help="Use the live LLM (requires the anthropic package).")
    p_ing.add_argument("--force", action="store_true",
                       help="Re-process every file even if unchanged.")
    p_ing.add_argument("--changed-only", action="store_true",
                       help="Only process new or changed files (default behaviour).")
    p_ing.add_argument("--dry-run", action="store_true",
                       help="Show what would change without writing anything.")
    p_ing.add_argument("--apply", action="store_true",
                       help="Explicitly apply changes (default; counterpart to --dry-run).")
    p_ing.add_argument("--review", action="store_true",
                       help=("Hold pages with risky phrases (\"confirmed malware\", etc.) "
                             "in the review queue instead of applying them directly."))
    p_ing.set_defaults(func=cmd_ingest)

    p_q = sub.add_parser(
        "query",
        help="Answer from the compiled wiki first.",
        description=(
            "Answer the given question using the compiled wiki and structured "
            "indexes. Falls back to raw-source lexical search only when the "
            "wiki has no compiled view of the topic, and says so clearly."
        ),
    )
    p_q.add_argument("case", help="<case_id>")
    p_q.add_argument("question", help="The question to ask.")
    p_q.set_defaults(func=cmd_query)

    p_rag = sub.add_parser(
        "rag-query",
        help="Run a simple raw-source retrieval baseline.",
        description=(
            "Naive BM25-style lexical search over raw_sources/. No synthesis, "
            "no contradiction handling. Ships as a baseline so the LLM Wiki "
            "answer can be compared against the 'ask my docs' status quo."
        ),
    )
    p_rag.add_argument("case", help="<case_id>")
    p_rag.add_argument("question", help="The question to ask.")
    p_rag.set_defaults(func=cmd_rag_query)

    p_cmp = sub.add_parser(
        "compare",
        help="Compare LLM Wiki answer against raw-source baseline.",
        description=(
            "Run both `query` and `rag-query` against the same question and "
            "print the two answers side by side. The fastest way to see why "
            "compiled wikis beat naive retrieval on synthesis questions."
        ),
    )
    p_cmp.add_argument("case", help="<case_id>")
    p_cmp.add_argument("question", help="The question to ask.")
    p_cmp.set_defaults(func=cmd_compare)

    p_l = sub.add_parser(
        "lint",
        help="Check the wiki for unsupported claims and contradictions.",
        description=(
            "Apply schema-defined lint rules. Four severity tiers: critical, "
            "high, medium, low. Exits non-zero on any critical or high finding."
        ),
    )
    p_l.add_argument("case", help="<case_id>")
    p_l.add_argument("--json", action="store_true",
                     help="Emit findings as JSON for machine consumption.")
    p_l.set_defaults(func=cmd_lint)

    p_r = sub.add_parser(
        "report",
        help="Generate the final-report draft.",
        description=(
            "Compose final_report.md from the current wiki state. Preserves "
            "the facts / inferences / hypotheses split; never promotes a "
            "hypothesis above its actual confidence."
        ),
    )
    p_r.add_argument("case", help="<case_id>")
    p_r.add_argument("--review", action="store_true",
                     help=("If the proposed report contains risky phrases, hold "
                           "it in the review queue instead of overwriting final_report.md."))
    p_r.set_defaults(func=cmd_report)

    p_e = sub.add_parser(
        "eval",
        help="Run the eval suite for the case.",
        description=(
            "Score the wiki's answers against evals/<case>_eval.json. "
            "Deterministic checks: must_include, must_not_include, "
            "required_sources, expect_refusal, expect_separation."
        ),
    )
    p_e.add_argument("case", help="<case_id>")
    p_e.add_argument("--verbose", action="store_true",
                     help="Show per-check results even for passing cases.")
    p_e.set_defaults(func=cmd_eval)

    p_ev = sub.add_parser(
        "evolve",
        help="Replay staged evidence drops and snapshot wiki evolution.",
        description=(
            "Walk raw_sources/<case>/step_NN_* in order, ingesting each step "
            "and snapshotting the wiki between steps. Produces "
            "benchmark_results/<case>/evolution_report.md and updates "
            ".fw/hypothesis_history.json."
        ),
    )
    p_ev.add_argument("case", help="<case_id>")
    p_ev.add_argument("--live", action="store_true",
                      help="Use the live LLM during ingestion.")
    p_ev.add_argument("--resume", action="store_true",
                      help="Do not wipe the existing wiki/snapshots before starting.")
    p_ev.add_argument("--key-question", default="Is this confirmed malware?",
                      help="Question to ask after each step to track assessment drift.")
    p_ev.set_defaults(func=cmd_evolve)

    p_bench = sub.add_parser(
        "benchmark",
        help="Score RAG vs LLM Wiki on eval questions.",
        description=(
            "Run every eval question through both the compiled wiki and the "
            "naive raw-source RAG baseline. Writes results.md and "
            "results.json under benchmark_results/<case>/."
        ),
    )
    p_bench.add_argument("case", help="<case_id>")
    p_bench.add_argument("--json", action="store_true",
                         help="Print the full BenchmarkSummary as JSON instead of markdown.")
    p_bench.set_defaults(func=cmd_benchmark)

    p_diff = sub.add_parser(
        "diff-snapshots",
        help="Show markdown diffs between two evolution snapshots.",
        description=(
            "Unified diff of every changed markdown page between two "
            "snapshots saved by `evolve`. Shows exactly when the wiki "
            "softened or revised its assessment."
        ),
    )
    p_diff.add_argument("case", help="<case_id>")
    p_diff.add_argument("snapshot_a", help="e.g. after_step_02_registry")
    p_diff.add_argument("snapshot_b", help="e.g. after_step_03_defender")
    p_diff.set_defaults(func=cmd_diff_snapshots)

    p_gb = sub.add_parser(
        "graph-build",
        help="Derive a relationship graph from the wiki indexes (GraphRAG-lite).",
        description=(
            "Build a deterministic file-based graph from the case's "
            ".fw/events.json + entities.json + claims.json. Writes "
            "graph.json, graph.md, and graph.mmd under .fw/."
        ),
    )
    p_gb.add_argument("case", help="<case_id>")
    p_gb.set_defaults(func=cmd_graph_build)

    p_gq = sub.add_parser(
        "graph-query",
        help="Answer a relationship question against the GraphRAG-lite graph.",
        description=(
            "Given an entity-shaped question, return that entity's "
            "relationships. The graph cannot answer current-assessment "
            "questions; for those, use `query`."
        ),
    )
    p_gq.add_argument("case", help="<case_id>")
    p_gq.add_argument("question", help="The relationship question to ask.")
    p_gq.set_defaults(func=cmd_graph_query)

    p_gx = sub.add_parser(
        "graph-export",
        help="Export the relationship graph to Mermaid / JSON / Markdown.",
        description=(
            "Re-renders the graph in the requested format. Mermaid is "
            "GitHub-renderable; JSON is the underlying Pydantic dump; "
            "Markdown is a human-readable node/edge summary."
        ),
    )
    p_gx.add_argument("case", help="<case_id>")
    p_gx.add_argument("--format", choices=["mermaid", "json", "md"],
                      default="mermaid",
                      help="Output format (default: mermaid).")
    p_gx.set_defaults(func=cmd_graph_export)

    p_ca = sub.add_parser(
        "compare-all",
        help="Run raw RAG, GraphRAG-lite, LLM Wiki, and hybrid side by side.",
        description=(
            "Print all four answer providers in one terminal so the "
            "differences are visible. See docs/llm_wiki_vs_rag_vs_graphrag.md."
        ),
    )
    p_ca.add_argument("case", help="<case_id>")
    p_ca.add_argument("question", help="The question to ask.")
    p_ca.set_defaults(func=cmd_compare_all)

    p_ex = sub.add_parser(
        "export-obsidian",
        help="Export the case wiki as an Obsidian-ready vault folder.",
        description=(
            "Copies the case's markdown pages (and graph.mmd if present) "
            "into examples/obsidian_vault_<case_id>/ along with an "
            "orientation README. The .fw/ sidecar is intentionally not "
            "exported — the vault is for human inspection only."
        ),
    )
    p_ex.add_argument("case", help="<case_id>")
    p_ex.set_defaults(func=cmd_export_obsidian)

    p_rv = sub.add_parser(
        "review",
        help="Manage the human-review queue for risky wiki updates.",
        description=(
            "Risky changes proposed under `ingest --review` or `report --review` "
            "are held in .fw/review_queue/ until a human approves or rejects. "
            "Use `review list` to see pending items, `review show <id>` to "
            "inspect, and `review approve|reject <id>` to decide."
        ),
    )
    p_rv.add_argument("review_action", choices=["list", "show", "approve", "reject"])
    p_rv.add_argument("case", help="<case_id>")
    p_rv.add_argument("review_id", nargs="?", default="", help="Required for show/approve/reject.")
    p_rv.add_argument("--status", choices=["pending", "approved", "rejected"],
                      default=None, help="Filter the list output by status.")
    p_rv.add_argument("--reason", default="",
                      help="Optional note recorded with the decision.")
    p_rv.set_defaults(func=cmd_review)

    p_bm = sub.add_parser(
        "benchmark-methods",
        help="Four-way deterministic benchmark across all answer providers.",
        description=(
            "Score every eval question against raw RAG / GraphRAG-lite / "
            "LLM Wiki / hybrid. Writes method_comparison.{md,json} under "
            "benchmark_results/<case>/."
        ),
    )
    p_bm.add_argument("case", help="<case_id>")
    p_bm.add_argument("--json", action="store_true",
                      help="Print the full MethodBenchmarkSummary as JSON.")
    p_bm.set_defaults(func=cmd_benchmark_methods)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
