# Forensic LLM Wiki

> **Forensic LLM Wiki is a markdown-first AI investigation system that
> compiles raw forensic evidence into an evolving Obsidian-compatible
> case wiki instead of answering from raw snippets every time like
> traditional RAG.**

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![Tests: 196 passing](https://img.shields.io/badge/tests-196%20passing-brightgreen.svg)
![Ruff: clean](https://img.shields.io/badge/ruff-clean-success.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)
![Markdown-first](https://img.shields.io/badge/markdown-first-blueviolet.svg)
![LLM Wiki](https://img.shields.io/badge/pattern-LLM%20Wiki-purple.svg)

---

## The thesis

> **RAG retrieves. GraphRAG relates. LLM Wiki maintains evolving case state. Hybrid combines them.**

| Method | Best at | Weak at |
|---|---|---|
| **Raw RAG** | Direct lookup from raw files | No persistent case state |
| **GraphRAG-lite** | Entity relationships | Weak narrative / current assessment |
| **LLM Wiki** | Hypotheses, contradictions, evolving state | Requires schema / lint discipline |
| **Hybrid** | Combining relationships + maintained state | More moving parts |

Traditional RAG retrieves raw snippets at query time. GraphRAG improves
relationship-aware retrieval. Forensic LLM Wiki maintains a persistent
investigation state — *what is currently believed, what supports it,
what contradicts it, and how that belief changed as new evidence arrived*
— and answers from that compiled state, not from raw retrieval.

## Architecture

```
raw_sources/       immutable evidence (LLM may read, never write)
       │ ingest
schema/            page templates + citation rules + lint rules
       │ controls
wiki/cases/<id>/   markdown investigation state
                   index, timeline, entities, iocs,
                   hypotheses, contradictions,
                   open_questions, final_report
                   .fw/   structured indexes + manifest + traces +
                          hypothesis_history + graph + review_queue
       │
query · lint · report · benchmark · MCP server · Obsidian export
```

Mermaid version: [`assets/architecture.mmd`](assets/architecture.mmd).
Side-by-side classic-RAG vs LLM Wiki: [`assets/rag_vs_llm_wiki.mmd`](assets/rag_vs_llm_wiki.mmd).
Detailed walkthrough: [`docs/architecture.md`](docs/architecture.md).

## Benchmark snapshot

Two scorecards are committed under
[`benchmark_results/`](benchmark_results/). Both use deterministic
substring + refusal checks — no LLM-as-judge.

### Method comparison on `case_002_evolving` (23 questions, 8 categories)

| Metric | Raw RAG | GraphRAG-lite | LLM Wiki | Hybrid |
|---|---:|---:|---:|---:|
| Passed | 7 / 23 | 5 / 23 | 19 / 23 | **20 / 23** |
| Relationship coverage | 0.60 | 0.60 | 0.80 | **1.00** |
| Narrative state quality | 0.14 | 0.00 | 0.71 | **0.71** |
| Refusal accuracy | 0.33 | 0.00 | 0.75 | **0.75** |
| Contradiction misses | 2 | 2 | 0 | **0** |

In the 23-question method benchmark, Hybrid passed **20 / 23**, LLM Wiki
passed **19 / 23**, Raw RAG passed **7 / 23**, and GraphRAG-lite passed
**5 / 23**. GraphRAG-lite performed best on its intended niche
(relationship questions). LLM Wiki performed better on contradiction
tracking, refusal, and current investigation assessment. Hybrid
performed best overall. These results are scoped to this synthetic
benchmark and should not be read as a universal claim about RAG or
GraphRAG — see
[`docs/threats_to_validity.md`](docs/threats_to_validity.md).

### Two-way on `case_002_evolving` (16 questions)

| Metric | Raw RAG | LLM Wiki |
|---|---:|---:|
| Passed | 4 / 16 | **16 / 16** |
| Missing source failures | 14 | **0** |
| Contradiction misses | 2 | **0** |
| Refusal accuracy | 0.33 | **1.00** |

On the six-step synthetic evolving forensic case, the LLM Wiki query
path passed 16 / 16 deterministic eval checks while the raw lexical
RAG baseline passed 4 / 16. The eval score climbs monotonically as
evidence arrives across the six step subdirectories — **2 → 2 → 5 → 8
→ 11 → 16** of 16 — which is the compounding-knowledge claim made
visible.

### Adversarial overclaim case (`case_003_adversarial_overclaim`)

| Metric | Raw RAG | LLM Wiki |
|---|---:|---:|
| Passed | 2 / 11 | **11 / 11** |
| Unsupported claim failures | 2 | **0** |
| Refusal accuracy | 0.75 | **1.00** |

In the adversarial overclaim case, where the analyst notes assert
*"confirmed malware"* and *"data was exfiltrated"* without sufficient
supporting evidence, the wiki path passed 11 / 11 deterministic checks
while raw RAG passed 2 / 11. The wiki surfaces the Defender clean scan
and the inconclusive hash reputation as contradicting evidence and
treats the analyst note as an analyst claim, not as ground truth.

## 60-second demo

```bash
git clone <repo> && cd forensic-llm-wiki
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
bash examples/demo_commands.sh
```

End-to-end without an API key: ingest → query → side-by-side RAG
comparison → lint → report → evolve across six evidence drops →
diff-snapshots between two steps → four-way benchmark scorecard.
Expected output is documented at
[`examples/demo_expected_output.md`](examples/demo_expected_output.md).

---

## What this is

- **File-based.** A folder of markdown is the product. No database, no
  vector store, no server.
- **Markdown-first.** Every page is human-readable and rendered from
  a structured snapshot on every ingest, so markdown and state cannot
  drift.
- **Obsidian-compatible.** `[[wiki links]]` and Mermaid graphs render
  natively. `python fw.py export-obsidian <case>` writes a clean vault.
- **LLM-maintained.** The LLM proposes structured updates (Pydantic
  models); the orchestrator validates them; the renderer writes
  markdown. The LLM never writes files directly.
- **Schema-guided.** `schema/` defines required pages, page templates,
  citation rules, and lint rules. Both humans and the LLM read it.
- **Citation-backed.** Every fact carries a `Source: raw_sources/...`
  citation or a structured `claim_NNNN` / `evt_NNNN` / `ent_NNNN`
  reference. Lint flags any fact-shaped bullet without one.

## What this is not

- **Not a generic RAG chatbot.** The wiki is the product; the query
  command is a thin renderer of compiled state.
- **Not a vector-database demo.** No embeddings, no ANN search.
- **Not a malware verdict engine.** The wiki refuses confirmed-malware
  language unless backed by High-confidence hypotheses with multiple
  supporting bullets.
- **Not a replacement for forensic analysts.** It is a workspace that
  surfaces contradictions and refuses unsupported claims; it does not
  adjudicate cases.

## AI engineering decisions

The decisions that distinguish this from a wrapper around an LLM call:

- **Immutable raw sources.** `raw_sources/` is the only ground-truth
  layer. The LLM may read it; it may never modify it.
- **Pydantic at every LLM-to-wiki boundary.** Extraction returns a
  validated `ExtractedFacts` instance. Invalid structures fail
  validation and cannot reach disk.
- **Schema-controlled markdown.** `schema/wiki_schema.md`,
  `schema/page_templates.md`, `schema/citation_rules.md`, and
  `schema/lint_rules.md` define what a "good" wiki page looks like.
- **Facts / inferences / hypotheses / contradictions are separated.**
  Hypothesis pages enforce a five-subsection template. Confidence is
  declared, not implied.
- **Lint refuses unsupported claims.** Four severity tiers. Critical
  findings include unattributed "confirmed malware" assertions and
  final-report claim IDs that don't exist in `.fw/claims.json`.
- **Risky updates can be held for human review.** `ingest --review` and
  `report --review` route content with risky phrases into
  `.fw/review_queue/` instead of applying them automatically.
- **Adversarial overclaim case** (`case_003_adversarial_overclaim`)
  tests whether the wiki blindly trusts analyst notes. It does not.
- **Mock LLM mode is deterministic.** Tests, CI, and the demo flow run
  reproducibly without an API key. Live LLM mode is an opt-in extra.
- **Benchmarks are deterministic.** `must_include`, `must_not_include`,
  `required_sources`, refusal heuristic, contradiction category checks
  — no LLM-as-judge.
- **MCP server** exposes 13 tools so an agent can read pages,
  ingest evidence, query, lint, generate the report, compare methods,
  walk the relationship graph, and pull hypothesis history /
  contradictions / open questions. Path traversal is blocked and the
  `.fw/` sidecar is off-limits to reads.

## Software engineering decisions

- **Modular CLI.** `fw.py` is a thin dispatcher. Each subcommand calls
  a function in `src/<operation>.py`. The same functions back the MCP
  tools.
- **Three on-disk layers, four CLI verbs** for Phase 1; further
  commands add evolve / benchmark / graph / compare-all / review /
  export-obsidian on top of them.
- **Stable IDs.** Every event, entity, and hypothesis gets
  `evt_NNNN` / `ent_NNNN` / `claim_NNNN` that survives re-ingest, so
  citations from the final report don't break across runs.
- **Incremental ingestion with a source manifest.** `.fw/manifest.json`
  hashes every raw file. Unchanged files are skipped by default;
  `--force` reprocesses everything; `--dry-run` previews diffs.
- **Path-traversal protection.** `read_wiki_page` resolves paths
  against the case dir and refuses anything that escapes it. The
  `.fw/` sidecar is sealed off from MCP reads.
- **Audit trail.** Every operation appends to `.fw/traces.jsonl`.
  Every review decision appends to `.fw/review_history.jsonl`.
- **196 tests** across 17 files, all in mock mode, no API key.
  `pytest` runs in ~6 s on a laptop.
- **Ruff clean.** Style + import hygiene + bug-prone-pattern checks
  pass cleanly.
- **CI on Python 3.11 and 3.12** via GitHub Actions. The workflow runs
  `ruff check`, `pytest`, and a smoke-test of the demo flow.
- **Explicit non-goals** documented in `CONTRIBUTING.md` (no FastAPI,
  no Postgres, no vector store, no frontend, no LangChain, no Neo4j,
  no LLM-as-judge).
- **Reproducible benchmark output.** Scorecards are committed under
  `benchmark_results/`. `make launch-check` is the single command
  that gates a release.

## CLI overview

```bash
# Compile evidence into the wiki
python fw.py ingest raw_sources/case_001 --dry-run
python fw.py ingest raw_sources/case_001 --apply
python fw.py ingest raw_sources/case_001 --review        # hold risky pages

# Query the compiled wiki
python fw.py query case_001 "Is this confirmed malware?"
python fw.py rag-query case_001 "Is this confirmed malware?"
python fw.py compare case_001 "Is this confirmed malware?"

# Lint and report
python fw.py lint case_001
python fw.py lint case_001 --json
python fw.py eval case_001
python fw.py report case_001 --review

# Step-by-step evolution + per-step snapshots
python fw.py evolve case_002_evolving
python fw.py diff-snapshots case_002_evolving \
    after_step_02_registry after_step_03_defender

# GraphRAG-lite + four-way comparison
python fw.py graph-build case_002_evolving
python fw.py graph-query case_002_evolving "What is DeskRest.exe related to?"
python fw.py graph-export case_002_evolving --format mermaid
python fw.py compare-all case_002_evolving "Is this confirmed malware?"

# Benchmarks
python fw.py benchmark case_002_evolving
python fw.py benchmark-methods case_002_evolving

# Obsidian export + human review queue
python fw.py export-obsidian case_002_evolving
python fw.py review list    case_002_evolving
python fw.py review show    case_002_evolving review_0001
python fw.py review approve case_002_evolving review_0001
python fw.py review reject  case_002_evolving review_0001
```

`python fw.py --help` lists every subcommand with a one-line
description.

## Agent-native usage through MCP

```bash
pip install -e ".[dev,mcp]"
python -m mcp_server.server
```

The server exposes 13 tools: `list_cases`, `get_case_summary`,
`list_wiki_pages`, `read_wiki_page`, `ingest_case_sources`,
`query_case`, `lint_case`, `generate_report`, `compare_all_methods`,
`get_hypothesis_history`, `get_contradictions`, `get_open_questions`,
`graph_query`. The agent uses the wiki as maintained working memory,
not as raw document search. See
[`docs/mcp_setup.md`](docs/mcp_setup.md) for a generic client config
and [`docs/agent_demo.md`](docs/agent_demo.md) for example tool-call
traces.

## Obsidian workflow

```bash
python fw.py export-obsidian case_002_evolving
```

Writes a clean vault to `examples/obsidian_vault_case_002_evolving/`
— markdown pages + `graph.mmd` + an orientation README; no internal
`.fw/`. Open in Obsidian for graph view, backlinks, and Mermaid
rendering. Full guidance in
[`docs/obsidian_workflow.md`](docs/obsidian_workflow.md).

## Human review for risky conclusions

```bash
python fw.py ingest raw_sources/case_002_evolving --review
python fw.py report case_002_evolving --review
python fw.py review approve case_002_evolving review_0001
```

The `--review` flag routes pages containing risky phrases
(*confirmed malware*, *exfiltration occurred*, *data was stolen*, …)
into `.fw/review_queue/` instead of writing them to disk. A human
approves or rejects; every decision lands in
`.fw/review_history.jsonl`. The review queue is also exposed via the
`ingest_case_sources` and `generate_report` MCP tools. Full design
notes in [`docs/human_review.md`](docs/human_review.md).

## Why not just GraphRAG?

GraphRAG is useful for relationship-aware retrieval. This project
includes a deterministic **GraphRAG-lite** baseline (`src/graph/`) for
exactly that reason. But forensic investigation also needs
**persistent narrative state**: hypotheses, contradictions, open
questions, confidence changes, and report drafts. The LLM Wiki layer
maintains that evolving state; the graph layer helps with
relationships.

> **GraphRAG answers:** *"What is connected to what?"*
> **LLM Wiki answers:** *"What do we currently believe, why, what
> contradicts it, and how did that belief change?"*

See [`docs/why_llm_wiki.md`](docs/why_llm_wiki.md) and
[`docs/llm_wiki_vs_rag_vs_graphrag.md`](docs/llm_wiki_vs_rag_vs_graphrag.md).

## Tests

```bash
pytest                # 196 tests, mock mode, no API key required
ruff check .
make launch-check     # pytest + ruff + python fw.py --help
```

The test suite covers: the three-layer architecture; ingest
correctness (manifest dedup, force, dry-run, recursive walk);
structured indexes and stable IDs; lint coverage (four severity
tiers, JSON output, attribution-aware C1, exfiltration C4, final-report
claim-ID check H4, meta-finding C5); query format and raw-source
fallback; rag-query and compare; eval runner; traces and ingestion
log; evolve walking every step and snapshotting; benchmark beating
raw RAG on the synthetic case; snapshot diffs; GraphRAG-lite graph
build and query; four-way method benchmark; review queue and
audit trail; Obsidian export; MCP tool functions (including path
traversal and sidecar lock-out); the adversarial overclaim case
refusing each unsupported claim; and presence + content of every doc
in the launch checklist.

## Limitations

Brief list — see [`docs/threats_to_validity.md`](docs/threats_to_validity.md)
for the long version.

- The benchmark is synthetic and small (three demo cases, 50-odd eval
  questions total).
- The raw-RAG baseline is lexical (BM25-style), not vector.
- **GraphRAG-lite is a deterministic local graph baseline, not
  Microsoft GraphRAG.** Cluster summaries, community detection, and
  hierarchical summarisation are not implemented.
- Deterministic mock LLM mode differs from real LLM behaviour. The
  numbers in this README are mock-mode results.
- Benchmarks use deterministic substring + refusal checks — no
  LLM-as-judge.
- No EVTX / MFT / prefetch / PCAP parsers yet.
- No production security sandbox; treat live-mode inputs as untrusted.
- No multi-user access control. The CLI and MCP server trust their
  caller.
- The risky-phrase detector is substring-based with an attribution
  override; novel paraphrases would slip through without a schema
  update.
- Not a malware verdict engine.

## Future work

- LLM-as-judge scoring layered on top of the deterministic checks.
- More demo cases sampled from public forensic write-ups.
- A real vector-RAG baseline (embeddings + reranker) alongside the
  lexical one.
- A real GraphRAG implementation as a third comparison.
- Local-model mode (Ollama, llama.cpp) for air-gapped use.
- Richer forensic parsers: EVTX, MFT, prefetch, PCAP.
- Obsidian plugin for in-place ingest.
- Multi-reviewer queue with role-based approval.

## Further reading

**Architecture & comparison**

- [`docs/architecture.md`](docs/architecture.md) — three-layer model, four verbs, ID model, snapshots.
- [`docs/rag_vs_llm_wiki.md`](docs/rag_vs_llm_wiki.md) — worked examples vs raw RAG.
- [`docs/why_llm_wiki.md`](docs/why_llm_wiki.md) — wiki vs graph: where each fits.
- [`docs/llm_wiki_vs_rag_vs_graphrag.md`](docs/llm_wiki_vs_rag_vs_graphrag.md) — four-way comparison table.

**Agent / human workflow**

- [`docs/mcp_setup.md`](docs/mcp_setup.md) — MCP tool surface and generic client config.
- [`docs/agent_demo.md`](docs/agent_demo.md) — example agent tool-call traces.
- [`docs/obsidian_workflow.md`](docs/obsidian_workflow.md) — exporting and browsing the vault.
- [`docs/human_review.md`](docs/human_review.md) — review queue: what counts as risky, approve/reject flow.

**Demo & evaluation**

- [`docs/demo_script.md`](docs/demo_script.md) — 5-minute live demo.
- [`docs/demo_video_script.md`](docs/demo_video_script.md) — 2 – 3-minute recordable demo.
- [`docs/benchmark_methodology.md`](docs/benchmark_methodology.md) — exactly how scoring works.
- [`examples/live_llm_smoke_test.md`](examples/live_llm_smoke_test.md) — running with a real model.

**Credibility**

- [`docs/threats_to_validity.md`](docs/threats_to_validity.md) — honest limits of the benchmark.
- [`docs/interview_talking_points.md`](docs/interview_talking_points.md) — concise technical answers.
- [`docs/launch_checklist.md`](docs/launch_checklist.md) — gate before publishing.

**Top-level**

- [`CASE_STUDY.md`](CASE_STUDY.md) — full technical case study.
- [`PROJECT_SUMMARY.md`](PROJECT_SUMMARY.md) — recruiter / interviewer summary with resume bullet.

## License

[MIT](LICENSE).
