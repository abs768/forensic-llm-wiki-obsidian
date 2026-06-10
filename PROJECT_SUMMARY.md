# Project Summary — Forensic LLM Wiki

A one-page overview for recruiters, interviewers, and reviewers.

## One-paragraph overview

Forensic LLM Wiki is a markdown-first AI investigation system that
compiles raw forensic evidence into an evolving Obsidian-compatible
case wiki — instead of answering from raw snippets every time like
traditional RAG. The wiki accumulates timeline, entities, IOCs,
hypotheses with separated facts / inferences / supporting /
contradicting evidence, an explicit contradictions ledger, open
questions, and a final-report draft. Every fact carries a citation;
risky updates can be held for human review; agents can drive the
whole system through an MCP server; and the wiki is plain markdown so
any analyst can open the case in Obsidian. Deterministic benchmarks
compare it against a raw lexical RAG baseline and a GraphRAG-lite
relationship-graph baseline. *RAG retrieves. GraphRAG relates. LLM
Wiki maintains evolving case state. Hybrid combines them.*

## Problem

Retrieval-Augmented Generation has no persistent investigation state.
It re-searches the same corpus on every question, cannot reconcile
contradicting evidence, and cheerfully repeats the loudest matching
line — for example, an analyst's *"confirmed malware"* note that
turns out to be unsupported. Forensic investigation needs accumulation:
timelines that grow, entities that recur, IOCs that get cross-referenced,
hypotheses with declared confidence, an explicit contradictions
ledger, open questions, and a report draft that separates facts from
inferences.

## Solution

A markdown-first AI investigation wiki, maintained by an LLM but
governed by explicit schema rules. Raw evidence is immutable. The LLM
proposes Pydantic-validated structured updates; the orchestrator
merges; the renderer writes markdown. Lint rules refuse unsupported
claims. A human review queue holds risky updates until a human
approves. An MCP server exposes the wiki as 13 tools so an agent can
maintain or query it.

## Architecture

```
raw_sources/       immutable evidence
       │ ingest
schema/            page templates + citation rules + lint rules
       │ controls
wiki/cases/<id>/   markdown investigation state + .fw/ sidecar
       │
query · lint · report · benchmark · evolve · graph-* · compare-all ·
review · export-obsidian · MCP server
```

The four core verbs (`ingest`, `query`, `lint`, `report`) are
file-based. The wiki has stable IDs (`evt_NNNN`, `ent_NNNN`,
`claim_NNNN`) that survive re-ingest, a manifest that tracks source
hashes for incremental ingestion, and `.fw/traces.jsonl` for an audit
trail.

## Why LLM Wiki instead of GraphRAG?

GraphRAG is useful for relationship-aware retrieval. The project
includes a GraphRAG-lite baseline for exactly that reason. But
forensic investigation also needs persistent narrative state:
hypotheses, contradictions, open questions, confidence changes, and
report drafts. The LLM Wiki layer maintains that evolving state; the
graph layer helps with relationships.

> **GraphRAG answers:** *"What is connected to what?"*
> **LLM Wiki answers:** *"What do we currently believe, why, what
> contradicts it, and how did that belief change?"*

## AI engineering highlights

- The LLM is not allowed to write files directly. Outputs are
  validated through Pydantic before they can reach the wiki.
- Raw sources are immutable; every fact carries a citation back to
  them.
- Markdown is the compiled knowledge layer; `.fw/*.json` is derived,
  not authoritative.
- Schema controls page structure, citation rules, and lint severity.
- Facts, inferences, hypotheses, and contradictions are separated in
  every hypothesis page.
- Unsupported claims are refused at query time or flagged by lint.
- Risky assertions like *"confirmed malware"* or *"exfiltration
  occurred"* can be routed into a human review queue.
- Adversarial overclaim case tests whether the wiki blindly trusts
  analyst notes — it does not.
- Deterministic mock mode keeps tests reproducible without API keys.
- Benchmarks are deterministic substring + refusal + category checks,
  not LLM-as-judge.
- An MCP server exposes 13 tools for agent-native workflows;
  path-traversal is blocked and the `.fw/` sidecar is off-limits to
  reads.

## Software engineering highlights

- Around 5 KLOC across `src/`, `mcp_server/`, and `fw.py`. Modular CLI
  where each subcommand calls a function in `src/<op>.py`.
- 196 tests across 17 files, all in mock mode, no API key required.
- Ruff clean. CI on Python 3.11 and 3.12.
- Incremental ingestion with manifest + source hashes (`--dry-run`,
  `--force`, `--changed-only`).
- Audit trail across three files: `.fw/traces.jsonl`,
  `.fw/ingestion_log.jsonl`, `.fw/review_history.jsonl`.
- Benchmark scorecards committed under `benchmark_results/` so the
  numbers are reproducible from a clean clone.
- Explicit non-goals in `CONTRIBUTING.md` (no FastAPI, no database,
  no vector store, no frontend, no LangChain, no Neo4j, no
  LLM-as-judge).
- `make launch-check` runs `pytest` + `ruff check` + `python fw.py
  --help` and is the single gate for a release.

## Agent and human workflow

The architecture is designed so **agents maintain the wiki, humans
inspect it, raw evidence stays immutable**. Three concrete pieces make
that real.

- **MCP server** exposes 13 tools (list cases, read a page with
  path-traversal blocked, ingest with or without `--review`, query
  the wiki, lint, generate the report, compare all four answer
  methods, walk the graph, pull hypothesis history /
  contradictions / open questions).
- **Obsidian export** writes a clean vault (markdown + `graph.mmd` +
  orientation README, no internal sidecar). The wiki is plain
  markdown; Obsidian renders it natively.
- **Human review queue** holds risky wiki updates (*confirmed
  malware*, *exfiltration occurred*, …) until a human approves or
  rejects, with every decision appended to
  `.fw/review_history.jsonl`.

## Benchmark summary

All scoring is deterministic. No LLM-as-judge.

- **`case_002_evolving` (16 questions).** LLM Wiki passed 16 / 16;
  raw lexical RAG passed 4 / 16. Refusal accuracy 1.00 vs 0.33. Per-step
  eval climbs 2 → 2 → 5 → 8 → 11 → 16 of 16 as evidence arrives.
- **`case_002_evolving_methods_eval` (23 questions, 4 providers).**
  Hybrid passed 20 / 23, LLM Wiki 19 / 23, Raw RAG 7 / 23, GraphRAG-lite
  5 / 23. GraphRAG-lite was best on its intended niche (relationship
  questions). LLM Wiki was better on contradiction tracking, refusal,
  and current assessment. Hybrid was best overall.
- **`case_003_adversarial_overclaim` (11 questions).** Wiki passed
  11 / 11; raw RAG passed 2 / 11. Refusal accuracy 1.00 vs 0.75. The
  wiki refused the analyst's *"confirmed malware"* and *"data was
  exfiltrated"* overclaims and surfaced the Defender clean scan and
  inconclusive hash reputation as contradicting evidence.

These results are scoped to a synthetic evolving forensic benchmark
and should not be read as a universal claim about RAG or GraphRAG.

## Limitations

- Benchmark is synthetic and small (three demo cases, ~50 eval
  questions total).
- Raw-RAG baseline is lexical, not vector.
- GraphRAG-lite is a deterministic local graph, not Microsoft
  GraphRAG.
- Mock LLM mode is used for tests; real LLM behaviour will differ.
- No EVTX / MFT / PCAP parsers yet.
- No production security sandbox, no multi-user access control.
- The risky-phrase detector is substring-based with an attribution
  override; novel paraphrases would slip through without a schema
  update.
- Not a malware verdict engine.
- See `docs/threats_to_validity.md` for the long form.

## Resume bullet

> Built **Forensic LLM Wiki**, a markdown-first AI investigation
> system that compiles raw forensic evidence into an evolving
> Obsidian-compatible case wiki with timelines, IOCs, hypotheses,
> contradictions, citation-backed claims, linting, MCP agent tools,
> human review, and benchmarks against raw RAG, GraphRAG-lite, and
> hybrid baselines.

*~5 KLOC, 196 tests, ruff-clean, no API key required for tests.*

## Try it

```bash
git clone <repo> && cd forensic-llm-wiki
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
bash examples/demo_commands.sh
```

Full case study in `CASE_STUDY.md`. Talking points in
`docs/interview_talking_points.md`. Honest limits in
`docs/threats_to_validity.md`.
