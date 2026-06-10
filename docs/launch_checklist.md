# Launch checklist

Tick everything before publishing the repo or recording a demo.
All boxes are currently green on `main` — this list is the runbook to
keep them green after every change.

## Repo health

- [x] `pytest` passes from a fresh clone (`pytest` → 163+ tests, mock mode)
- [x] `ruff check .` is clean
- [x] `python fw.py --help` lists every subcommand with a one-line description
- [x] CI is green (`.github/workflows/test.yml`, Python 3.11 and 3.12)
- [x] `requirements.txt` and `pyproject.toml` agree
- [x] `pip install -e ".[dev]"` works on a clean Python 3.11+ venv
- [x] `LICENSE` exists (MIT) and is dated to the publication year

## README

- [x] README explains the project in 30 seconds (hook → thesis → architecture → benchmark → demo command)
- [x] One-sentence hook is the first non-title line
- [x] Method-comparison table (RAG / GraphRAG-lite / LLM Wiki / Hybrid) visible without scrolling
- [x] Benchmark numbers in the README match the committed `benchmark_results/case_002_evolving/results.md`
- [x] Architecture diagram visible near the top (`assets/architecture.mmd`)
- [x] "Why not just GraphRAG?" section answers the obvious objection
- [x] "Threats to validity" link is present and easy to find

## Documentation

- [x] `CASE_STUDY.md` exists at repo root
- [x] `PROJECT_SUMMARY.md` exists at repo root with a resume bullet
- [x] `docs/threats_to_validity.md` exists and is honest
- [x] `docs/interview_talking_points.md` exists
- [x] `docs/launch_checklist.md` (this file) exists
- [x] `docs/demo_video_script.md` exists
- [x] `docs/architecture.md` exists
- [x] `docs/rag_vs_llm_wiki.md` exists
- [x] `docs/why_llm_wiki.md` exists
- [x] `docs/llm_wiki_vs_rag_vs_graphrag.md` exists
- [x] `docs/mcp_setup.md` exists
- [x] `docs/agent_demo.md` exists
- [x] `docs/obsidian_workflow.md` exists
- [x] `docs/human_review.md` exists
- [x] `docs/benchmark_methodology.md` exists
- [x] `docs/demo_script.md` exists
- [x] `examples/live_llm_smoke_test.md` exists

## Demo assets

- [x] `examples/demo_commands.sh` runs end-to-end without API keys
- [x] `examples/demo_expected_output.md` matches what `demo_commands.sh` actually prints
- [x] `examples/sample_questions.md` exists
- [x] `examples/obsidian_vault_case_002/` exists and opens cleanly in Obsidian
- [x] `examples/obsidian_vault_template/` exists with five page templates
- [x] `assets/architecture.mmd` exists
- [x] `assets/rag_vs_llm_wiki.mmd` exists
- [x] `assets/method_comparison_table.md` exists
- [x] `assets/demo_flow.md` exists

## Cases and benchmarks

- [x] `raw_sources/case_001/` exists (Phase 1 demo)
- [x] `raw_sources/case_002_evolving/step_NN_*/` six step subdirs exist (Phase 3)
- [x] `raw_sources/case_003_adversarial_overclaim/` exists (Phase 7)
- [x] `evals/case_001_eval.json` exists
- [x] `evals/case_002_evolving_eval.json` exists
- [x] `evals/case_002_evolving_methods_eval.json` exists
- [x] `evals/case_003_adversarial_overclaim_eval.json` exists
- [x] `benchmark_results/case_002_evolving/results.md` committed
- [x] `benchmark_results/case_002_evolving/evolution_report.md` committed
- [x] `benchmark_results/case_002_evolving/method_comparison.md` committed
- [x] `benchmark_results/case_003_adversarial_overclaim/results.md` committed

## MCP / Obsidian / review

- [x] `mcp_server/` package imports without the `mcp` SDK (tools are SDK-free)
- [x] `mcp_server/README.md` exists
- [x] `read_wiki_page` blocks path traversal and the `.fw/` sidecar (test covers both)
- [x] `fw.py export-obsidian <case>` writes a clean vault (no sidecar)
- [x] `fw.py review {list|show|approve|reject}` work end-to-end (test covers each)
- [x] `--review` flag on `ingest` and `report` is wired and tested
- [x] Risky-phrase scanner is attribution-aware (test covers quoted-vs-asserted)

## Launch metadata

- [x] Resume bullet is in `PROJECT_SUMMARY.md` and ready to copy-paste
- [x] LinkedIn post draft talking points are in `docs/interview_talking_points.md`
- [x] 2-minute demo plan exists at `docs/demo_video_script.md`
- [ ] (Optional) A live-LLM smoke-test recording exists under
      `examples/live_runs/` — see `examples/live_llm_smoke_test.md`

## Final command sweep

```bash
make launch-check
```

`launch-check` runs `pytest`, `ruff check .`, and `python fw.py --help`
in sequence and is the single command this checklist boils down to.
