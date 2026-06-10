# Interview talking points

Concise, technical answers to the questions a recruiter or interviewer
is likely to ask. Each section is two or three sentences — long enough
to be substantive, short enough to deliver out loud.

## What problem does this solve?

Retrieval-Augmented Generation has no persistent state, so it answers
each forensic question from scratch and cannot reconcile contradicting
evidence in the same corpus. Forensic LLM Wiki maintains a
citation-backed markdown investigation wiki that accumulates timeline,
entities, IOCs, hypotheses, contradictions, and open questions as
evidence arrives. Answers come from the compiled case state, not from
raw retrieval.

## Why not traditional RAG?

Traditional RAG retrieves raw chunks at query time. It has no place to
keep accumulated hypotheses, no contradictions ledger, and no refusal
discipline. In the included demo, raw lexical RAG retrieves the
analyst's "possible malware infection" line and cannot reconcile it
against the Defender clean scan from the same corpus.

## Why not just GraphRAG?

GraphRAG is useful for relationship-aware retrieval. This project
includes a GraphRAG-lite baseline for exactly that reason. But
forensic investigation also needs persistent narrative state:
hypotheses, contradictions, open questions, confidence changes, and
report drafts. The LLM Wiki layer maintains that evolving state,
while the graph layer helps with relationships.

## What is the architecture?

Three on-disk layers and four core CLI verbs. `raw_sources/` is
immutable evidence. `schema/` is markdown rules that control how the
wiki is maintained. `wiki/cases/<id>/` is the LLM-maintained markdown
plus a `.fw/` sidecar (state, manifest, structured indexes, traces,
hypothesis history, graph, review queue). The four verbs are `ingest`,
`query`, `lint`, `report`; later phases add `evolve`, `benchmark`,
`graph-*`, `compare-all`, `export-obsidian`, `review`.

## What was hardest?

Not generating markdown. The hard part was maintaining citation
discipline, separating facts from hypotheses, and preventing
overconfident forensic conclusions as evidence arrived incrementally.
Concretely: writing an attribution-aware risky-phrase detector so the
wiki can faithfully *quote* an analyst's "confirmed malware" overclaim
without itself asserting it; assigning stable `claim_NNNN` IDs that
survive re-ingest so report citations don't break; and running a
two-pass contradiction detector so order of ingestion doesn't change
the outcome.

## How did you evaluate it?

Three eval sets and three benchmark commands, all scored
deterministically. `case_002_evolving_eval.json` (16 questions) and
the matching four-way `case_002_evolving_methods_eval.json` (23
questions across 8 categories) measure ordinary forensic reasoning.
`case_003_adversarial_overclaim_eval.json` (11 questions) measures
whether the wiki refuses analyst overclaims. Scoring uses
`must_include` / `must_not_include` / `required_sources` / refusal /
category checks — no LLM-as-judge. All scorecards are committed
under `benchmark_results/`.

## How do you prevent hallucinations?

The system does not rely on generation alone. Raw sources are
immutable, LLM outputs are validated through Pydantic, claims carry
source / event / entity IDs, lint flags unsupported conclusions, and
risky assertions like "confirmed malware" or "exfiltration occurred"
can be routed into a human review queue. The query layer also refuses
specific overclaims by routing them through a confirmation builder
that surfaces structured contradictions instead of echoing raw lines.

## How does human review work?

`fw.py ingest --review` and `fw.py report --review` scan freshly
rendered content for risky phrases. If any are present in
unattributed positions, the page is held back on disk and the proposed
content is queued as JSON under `.fw/review_queue/`. A human runs
`fw.py review list | show | approve | reject <case> <id>`. Approving
writes the proposed content; rejecting leaves the wiki unchanged.
Every decision lands in `.fw/review_history.jsonl` for an auditable
chain of custody. The same flag is exposed through the
`ingest_case_sources` and `generate_report` MCP tools.

## What would you build next?

A real vector-RAG and a real GraphRAG implementation as additional
baselines, so the comparison is not just against a lexical scorer and
a deterministic local graph. LLM-as-judge scoring layered on top of
the deterministic checks. More demo cases sampled from public
forensic write-ups. Local-model mode (Ollama, llama.cpp) for
air-gapped use. Richer forensic parsers: EVTX, MFT, prefetch, PCAP.
A multi-reviewer queue with role-based approval.

## What are the limitations?

The benchmark is synthetic and small. The raw-RAG baseline is lexical,
not vector. GraphRAG-lite is a deterministic local graph, not Microsoft
GraphRAG. Deterministic mock mode is used for tests and CI; real LLM
behaviour will differ. No EVTX / MFT / PCAP parsers yet. No
production security sandbox. No multi-user access control. The
risky-phrase detector is substring-based with an attribution override
— novel paraphrases would slip through without a schema update. Not a
malware verdict engine. Full list in `docs/threats_to_validity.md`.

## How big is the codebase?

Around 5 KLOC across `src/`, `mcp_server/`, and `fw.py`. 196 tests
across 17 files, all in mock mode, no API key required. `pytest` runs
in about 6 seconds. Ruff clean. GitHub Actions runs the full suite
on Python 3.11 and 3.12.

## How would you demo this?

`bash examples/demo_commands.sh` runs the full flow end-to-end in
about 30 seconds: ingest, query, side-by-side RAG comparison, lint,
report, evolve across six steps, diff-snapshots between two steps,
and the four-way benchmark scorecard. A recordable 2 – 3-minute
version with voiceover is in `docs/demo_video_script.md`. A 5-minute
live walkthrough is in `docs/demo_script.md`.

## Elevator pitch

> RAG retrieves. GraphRAG relates. LLM Wiki maintains evolving case
> state. Hybrid combines them. Forensic LLM Wiki is a markdown-first
> AI investigation system that compiles raw forensic evidence into an
> evolving Obsidian-compatible case wiki, with deterministic
> benchmarks against a raw lexical RAG baseline, a GraphRAG-lite
> relationship-graph baseline, and a Hybrid that combines both.
