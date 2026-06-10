# Forensic LLM Wiki

> **Forensic LLM Wiki is a markdown-first AI investigation system that compiles raw forensic evidence into an evolving Obsidian-compatible case wiki instead of answering from raw snippets every time like traditional RAG.**

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![Tests: 196 passing](https://img.shields.io/badge/tests-196%20passing-brightgreen.svg)
![Ruff: clean](https://img.shields.io/badge/ruff-clean-success.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)
![Markdown-first](https://img.shields.io/badge/markdown-first-blueviolet.svg)
![LLM Wiki](https://img.shields.io/badge/pattern-LLM%20Wiki-purple.svg)

---

## Thesis

> **RAG retrieves. GraphRAG relates. LLM Wiki maintains evolving case state. Hybrid combines them.**

Traditional RAG retrieves raw snippets at query time. GraphRAG improves relationship-aware retrieval. Forensic LLM Wiki maintains a persistent investigation state: what is currently believed, what supports it, what contradicts it, and how that belief changes as new evidence arrives.

The system answers from a compiled investigation wiki, not from raw retrieval alone.

| Method            | Best at                                    | Weak at                             |
| ----------------- | ------------------------------------------ | ----------------------------------- |
| **Raw RAG**       | Direct lookup from raw files               | No persistent case state            |
| **GraphRAG-lite** | Entity relationships                       | Weak narrative / current assessment |
| **LLM Wiki**      | Hypotheses, contradictions, evolving state | Requires schema / lint discipline   |
| **Hybrid**        | Combining relationships + maintained state | More moving parts                   |

---

## Contents

* [Architecture](#architecture)
* [Benchmark snapshot](#benchmark-snapshot)
* [60-second demo](#60-second-demo)
* [What this is](#what-this-is)
* [Core capabilities](#core-capabilities)
* [CLI overview](#cli-overview)
* [MCP, Obsidian, and human review](#mcp-obsidian-and-human-review)
* [Tests and quality gates](#tests-and-quality-gates)
* [Limitations](#limitations)
* [Further reading](#further-reading)

---

## Architecture

```text
raw_sources/       immutable evidence
       │           LLM may read, never write
       ▼
schema/            page templates, citation rules, lint rules
       │           controls the wiki structure
       ▼
wiki/cases/<id>/   markdown investigation state
                   index.md
                   timeline.md
                   entities.md
                   iocs.md
                   hypotheses.md
                   contradictions.md
                   open_questions.md
                   final_report.md

                   .fw/
                   manifest.json
                   events.json
                   entities.json
                   claims.json
                   traces.jsonl
                   ingestion_log.jsonl
                   hypothesis_history.json
                   graph.json
                   review_queue/
                   review_history.jsonl
       │
       ▼
query · lint · report · benchmark · compare · graph · MCP · Obsidian
```

The core idea is simple:

* `raw_sources/` is immutable evidence.
* `schema/` defines how the investigation wiki should be structured.
* `wiki/cases/<id>/` is the maintained case state.
* `.fw/` stores structured sidecar data for reproducibility, linting, tracing, graph queries, and review history.

Markdown is the product. The wiki is human-readable, Obsidian-compatible, and regenerated from structured state so markdown and machine-readable indexes do not drift.

Architecture files:

* [`assets/architecture.mmd`](assets/architecture.mmd)
* [`assets/rag_vs_llm_wiki.mmd`](assets/rag_vs_llm_wiki.mmd)
* [`docs/architecture.md`](docs/architecture.md)

---

## Benchmark snapshot

Benchmark scorecards are committed under [`benchmark_results/`](benchmark_results/). Scoring is deterministic: substring checks, required-source checks, refusal checks, and category-bucketed evaluation. There is no LLM-as-judge.

These results are from synthetic forensic cases and should be read as architecture evidence, not universal claims about all RAG or GraphRAG systems. See [`docs/threats_to_validity.md`](docs/threats_to_validity.md).

### Four-way method comparison

`case_002_evolving`, 23 questions, 8 categories:

| Metric                  | Raw RAG | GraphRAG-lite | LLM Wiki |      Hybrid |
| ----------------------- | ------: | ------------: | -------: | ----------: |
| Passed                  |  7 / 23 |        5 / 23 |  19 / 23 | **20 / 23** |
| Relationship coverage   |    0.60 |          0.60 |     0.80 |    **1.00** |
| Narrative state quality |    0.14 |          0.00 |     0.71 |    **0.71** |
| Refusal accuracy        |    0.33 |          0.00 |     0.75 |    **0.75** |
| Contradiction misses    |       2 |             2 |        0 |       **0** |

Hybrid performed best overall. LLM Wiki performed better on contradiction tracking, refusal, and current investigation assessment. GraphRAG-lite performed best on its intended niche: relationship questions.

### Evolving case benchmark

`case_002_evolving`, 16 questions:

| Metric                  | Raw RAG |    LLM Wiki |
| ----------------------- | ------: | ----------: |
| Passed                  |  4 / 16 | **16 / 16** |
| Missing source failures |      14 |       **0** |
| Contradiction misses    |       2 |       **0** |
| Refusal accuracy        |    0.33 |    **1.00** |

The eval score improves as evidence arrives across six evidence drops:

```text
step_01_powershell        2 / 16
step_02_registry          2 / 16
step_03_defender          5 / 16
step_04_network           8 / 16
step_05_investigator_note 11 / 16
step_06_hash_reputation   16 / 16
```

This is the main compounding-knowledge claim: the maintained wiki becomes more useful as evidence accumulates.

### Adversarial overclaim case

`case_003_adversarial_overclaim` tests whether the system blindly trusts analyst notes.

The analyst note claims:

* “confirmed malware”
* “data was exfiltrated”
* “the attacker stole files”

The supporting evidence does not justify those conclusions.

| Metric                     | Raw RAG |    LLM Wiki |
| -------------------------- | ------: | ----------: |
| Passed                     |  2 / 11 | **11 / 11** |
| Unsupported claim failures |       2 |       **0** |
| Refusal accuracy           |    0.75 |    **1.00** |

The wiki treats the analyst note as an analyst claim, not as ground truth. It surfaces the Defender clean scan and inconclusive hash reputation as contradicting evidence.

---

## 60-second demo

```bash
git clone https://github.com/abs768/forensic-llm-wiki.git
cd forensic-llm-wiki

python3.11 -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"
bash examples/demo_commands.sh
```

The demo runs end-to-end without an API key:

```text
ingest
query
RAG comparison
lint
report
evolve across six evidence drops
snapshot diff
four-way benchmark
```

Expected output is documented in [`examples/demo_expected_output.md`](examples/demo_expected_output.md).

Run the release gate:

```bash
make launch-check
```

---

## What this is

* **Markdown-first.** The investigation wiki is the maintained knowledge layer.
* **File-based.** No database, no vector store, no web backend, no always-on application server.
* **Obsidian-compatible.** Exported vaults include markdown pages, wiki links, and Mermaid graphs.
* **Schema-guided.** Page templates, citation rules, and lint rules live in `schema/`.
* **Citation-backed.** Facts are tied to raw sources or structured IDs.
* **Agent-readable.** MCP tools expose query, lint, report, graph, review, and case-summary operations.
* **Human-reviewable.** Risky forensic conclusions can be routed into a review queue before landing in the wiki.

---

## What this is not

* **Not a generic RAG chatbot.** The wiki is the product; query is a view over maintained state.
* **Not a vector database demo.** The baseline is raw lexical RAG, not embeddings.
* **Not a malware verdict engine.** It refuses confirmed-malware language unless the evidence supports it.
* **Not a replacement for forensic analysts.** It helps maintain state, surface contradictions, and draft reports.
* **Not a production SOC platform.** There is no auth, multi-user control, sandboxing, or production deployment layer.

---

## Core capabilities

### AI engineering

* LLM outputs pass through Pydantic validation before reaching disk.
* Raw sources are immutable.
* Facts, inferences, hypotheses, contradictions, and open questions are separated.
* Every event, entity, and claim receives a stable ID.
* Unsupported claims are refused or linted.
* Risky claims such as “confirmed malware” and “exfiltration occurred” can be routed to human review.
* Benchmarks are deterministic and reproducible without an API key.
* MCP tools expose the maintained wiki to agents.

### Software engineering

* Modular Python CLI with 15 subcommands.
* `fw.py` is a thin dispatcher over modules in `src/`.
* Incremental ingestion uses a SHA-256 manifest.
* `--dry-run`, `--force`, and changed-only ingestion are supported.
* Structured traces, ingestion logs, and review history are written as JSONL.
* MCP `read_wiki_page` blocks path traversal and prevents `.fw/` sidecar reads.
* CI runs on Python 3.11 and 3.12.
* 196 tests pass in deterministic mock mode.
* Ruff is clean.
* Explicit non-goals are documented in [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## CLI overview

```bash
# Compile evidence into the wiki
python fw.py ingest raw_sources/case_001 --dry-run
python fw.py ingest raw_sources/case_001 --apply
python fw.py ingest raw_sources/case_001 --review

# Query the compiled wiki
python fw.py query case_001 "Is this confirmed malware?"
python fw.py rag-query case_001 "Is this confirmed malware?"
python fw.py compare case_001 "Is this confirmed malware?"

# Lint, evaluate, and report
python fw.py lint case_001
python fw.py lint case_001 --json
python fw.py eval case_001
python fw.py report case_001 --review

# Step-by-step evidence evolution
python fw.py evolve case_002_evolving
python fw.py diff-snapshots case_002_evolving \
    after_step_02_registry after_step_03_defender

# GraphRAG-lite and four-way comparison
python fw.py graph-build case_002_evolving
python fw.py graph-query case_002_evolving "What is DeskRest.exe related to?"
python fw.py graph-export case_002_evolving --format mermaid
python fw.py compare-all case_002_evolving "Is this confirmed malware?"

# Benchmarks
python fw.py benchmark case_002_evolving
python fw.py benchmark-methods case_002_evolving

# Obsidian export and human review
python fw.py export-obsidian case_002_evolving
python fw.py review list    case_002_evolving
python fw.py review show    case_002_evolving review_0001
python fw.py review approve case_002_evolving review_0001
python fw.py review reject  case_002_evolving review_0001
```

`python fw.py --help` lists all subcommands with descriptions.

---

## MCP, Obsidian, and human review

### MCP server

```bash
pip install -e ".[dev,mcp]"
python -m mcp_server.server
```

The MCP server exposes 13 tools:

```text
list_cases
get_case_summary
list_wiki_pages
read_wiki_page
ingest_case_sources
query_case
lint_case
generate_report
compare_all_methods
get_hypothesis_history
get_contradictions
get_open_questions
graph_query
```

The agent uses the maintained wiki as working memory, not raw document search.

Docs:

* [`docs/mcp_setup.md`](docs/mcp_setup.md)
* [`docs/agent_demo.md`](docs/agent_demo.md)

### Obsidian export

```bash
python fw.py export-obsidian case_002_evolving
```

This writes a clean vault to:

```text
examples/obsidian_vault_case_002_evolving/
```

The exported vault contains markdown pages, `graph.mmd`, and an orientation README. Internal `.fw/` sidecar files are not exported.

Docs:

* [`docs/obsidian_workflow.md`](docs/obsidian_workflow.md)

### Human review queue

```bash
python fw.py ingest raw_sources/case_002_evolving --review
python fw.py report case_002_evolving --review
python fw.py review list case_002_evolving
```

Risky conclusions are written to `.fw/review_queue/` instead of being applied automatically. Approve or reject decisions are appended to `.fw/review_history.jsonl`.

Docs:

* [`docs/human_review.md`](docs/human_review.md)

---

## Why not just GraphRAG?

GraphRAG is useful for relationship-aware retrieval. This project includes a deterministic GraphRAG-lite baseline for that reason.

But forensic investigation also needs persistent narrative state:

* hypotheses
* contradictions
* open questions
* confidence changes
* report drafts
* evidence history

GraphRAG answers:

> What is connected to what?

LLM Wiki answers:

> What do we currently believe, why, what contradicts it, and how did that belief change?

Docs:

* [`docs/why_llm_wiki.md`](docs/why_llm_wiki.md)
* [`docs/llm_wiki_vs_rag_vs_graphrag.md`](docs/llm_wiki_vs_rag_vs_graphrag.md)

---

## Tests and quality gates

```bash
pytest
ruff check .
make launch-check
```

Current status:

```text
196 tests passing
ruff clean
CI on Python 3.11 and 3.12
mock mode; no API key required
```

The test suite covers:

* ingest and manifest behavior
* stable event/entity/claim IDs
* structured indexes
* lint rules and JSON output
* query formatting
* raw RAG and compare flows
* eval runner
* traces and ingestion logs
* evolving-case snapshots
* GraphRAG-lite graph build/query/export
* four-way benchmark
* MCP tools
* path traversal protection
* Obsidian export
* human review queue
* adversarial overclaim refusal
* launch documentation artifacts

---

## Limitations

See [`docs/threats_to_validity.md`](docs/threats_to_validity.md) for the full version.

Important limitations:

* The benchmark is synthetic and small.
* The raw RAG baseline is lexical, not vector-based.
* GraphRAG-lite is a deterministic local graph baseline, not Microsoft GraphRAG.
* Mock LLM mode differs from live LLM behavior.
* Benchmarks use deterministic checks, not LLM-as-judge.
* There are no EVTX, MFT, prefetch, or PCAP parsers yet.
* There is no production security sandbox.
* There is no auth or multi-user access control.
* The risky-phrase detector is substring-based with an attribution override.
* This is not a malware verdict engine.

---

## Future work

* Add a vector-RAG baseline with embeddings and reranking.
* Add a full GraphRAG implementation as a stronger comparison.
* Add live LLM smoke-test scorecards.
* Add local-model mode for air-gapped environments.
* Add forensic parsers for EVTX, MFT, prefetch, and PCAP.
* Add an Obsidian plugin for in-place ingest.
* Add multi-reviewer approval workflow.

---

## Further reading

### Architecture and comparison

* [`docs/architecture.md`](docs/architecture.md)
* [`docs/rag_vs_llm_wiki.md`](docs/rag_vs_llm_wiki.md)
* [`docs/why_llm_wiki.md`](docs/why_llm_wiki.md)
* [`docs/llm_wiki_vs_rag_vs_graphrag.md`](docs/llm_wiki_vs_rag_vs_graphrag.md)

### Agent and human workflow

* [`docs/mcp_setup.md`](docs/mcp_setup.md)
* [`docs/agent_demo.md`](docs/agent_demo.md)
* [`docs/obsidian_workflow.md`](docs/obsidian_workflow.md)
* [`docs/human_review.md`](docs/human_review.md)

### Demo and evaluation

* [`docs/demo_script.md`](docs/demo_script.md)
* [`docs/demo_video_script.md`](docs/demo_video_script.md)
* [`docs/benchmark_methodology.md`](docs/benchmark_methodology.md)
* [`examples/live_llm_smoke_test.md`](examples/live_llm_smoke_test.md)

### Credibility

* [`docs/threats_to_validity.md`](docs/threats_to_validity.md)
* [`docs/interview_talking_points.md`](docs/interview_talking_points.md)
* [`docs/launch_checklist.md`](docs/launch_checklist.md)

### Top-level summaries

* [`CASE_STUDY.md`](CASE_STUDY.md)
* [`PROJECT_SUMMARY.md`](PROJECT_SUMMARY.md)

---

## License

[MIT](LICENSE)
