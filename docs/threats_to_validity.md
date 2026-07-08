# Threats to validity

This project demonstrates an architectural pattern — a markdown-first
LLM Wiki for forensic-style investigation — and benchmarks it against
three simple baselines. The benchmark numbers in `benchmark_results/`
are real and reproducible. They should not be over-read. This page
lists the honest limits.

> This project does not claim that LLM Wiki universally beats RAG or
> GraphRAG. It shows that, on a synthetic evolving forensic benchmark,
> a maintained markdown wiki can outperform a raw lexical RAG baseline,
> an embedding-based vector RAG baseline, and a deterministic
> GraphRAG-lite graph baseline on contradiction tracking, refusal
> accuracy, and narrative state maintenance.

## What the benchmark is and is not

- **Synthetic cases.** Three demo cases — `case_001`,
  `case_002_evolving` (six-step evolving demo), and
  `case_003_adversarial_overclaim` (analyst-overclaim stress test) —
  and about 50 total eval questions. The cases are scripted to expose
  differences between methods, not sampled from a population of real
  incidents.
- **Small N.** Statistical claims across arbitrary investigations are
  not supported by these numbers. Read them as worked examples that
  the architecture behaves as designed.
- **Deterministic scoring.** `must_include` / `must_not_include`
  substring checks, basename `required_sources` checks, a refusal
  heuristic, and category-bucketed accuracy. **No LLM-as-judge.**
  That makes the numbers reproducible but cannot distinguish a
  well-cited refusal from a scrambled one that happens to contain the
  right tokens.
- **No live LLM in tests.** The mock LLM mode runs the same parser /
  extractor pipeline a live LLM would post-process, so the wiki it
  produces is honest, but it does not capture creative free-form
  reasoning a real LLM might add. A real LLM is likely to be **more**
  capable on synthesis and **less** consistent across runs.

## What the baselines are

- **Raw RAG** is a small BM25-style lexical scorer over
  `raw_sources/`, shipped in `src/rag.py`. It is intentionally simple.
- **Vector RAG** is embedding retrieval (cosine top-k over line-window
  chunks), shipped in `src/vector_rag.py`. The committed scorecards use
  `sentence-transformers/all-MiniLM-L6-v2`; tests and CI use a
  deterministic hashed bag-of-words fallback so no model download is
  required. There is no reranker and no query rewriting. Better
  retrieval narrows the gap on lookup questions — but the gap on
  synthesis / refusal questions is structural, not a retrieval-quality
  artefact, and that is exactly what the five-way scorecard shows.
- **GraphRAG-lite** is a deterministic file-based relationship graph
  derived from the wiki's existing structured indexes. **It is not
  Microsoft GraphRAG.** It does no community detection, no cluster
  summaries, and no hierarchical summarisation. It is a small, honest
  stand-in chosen to make the relationship-vs-narrative distinction
  visible.

## What the system is not

- **Not a malware verdict engine.** The wiki refuses
  confirmed-malware language unless backed by High-confidence
  hypotheses with multiple supporting bullets. A real malware verdict
  requires sandbox, behavioural analysis, and human review that this
  project does not implement.
- **Not a replacement for forensic analysts.** The wiki is a
  workspace, not an adjudicator. It surfaces contradictions and
  refuses unsupported claims; deciding what they mean for a case is
  the analyst's job.
- **Not production incident-response software.** No SOAR, no security
  sandbox, no privilege boundaries, no multi-user access control, no
  audit trail beyond `.fw/traces.jsonl` and
  `.fw/review_history.jsonl`.
- **Not a forensic file-format toolkit.** Parsers cover representative
  samples (`powershell_history.txt`, `*.reg`, sysmon-shaped CSV,
  network CSV, AV text, hash reputation, investigator notes). **No
  EVTX, MFT, prefetch, PCAP, or memory-image parsers yet.**

## Specific gaps a reader should know about

- **No full EVTX parser.** Real Windows event logs are not handled.
- **No sandboxed hostile-file analysis.** The mock pipeline doesn't
  execute anything from raw sources, but a live LLM mode could in
  principle exfiltrate text it reads. Treat live-mode inputs as
  untrusted.
- **No auth or multi-user access control.** The CLI and the MCP server
  trust their caller.
- The **review queue** is single-reviewer. There is no notion of "who
  approved" beyond the timestamps in `review_history.jsonl`.
- The **hypothesis history's `assessment` field** is captured from a
  single key question per case, so it reflects only that one angle.
- The **risky-phrase detector** is substring-based with an
  attribution-aware override. A novel paraphrase ("the binary is 100%
  malware") would slip through; the scanner expects the canonical
  phrases the lint rules know about.
- **Snapshots** are full copies of `wiki/cases/<case>/`. Cheap for
  the demo, expensive for very large wikis.

## How to read the numbers in the scorecards

`benchmark_results/<case>/results.md`,
`benchmark_results/<case>/method_comparison.md`, and
`benchmark_results/case_002_evolving/evolution_report.md` are
committed to the repo. They were generated by `python fw.py
benchmark` and `python fw.py benchmark-methods` against the included
evals.

- Read them as **architecture evidence**, not as universal proof.
- The Hybrid provider winning overall demonstrates that combining
  relationship structure with maintained narrative state is the right
  default for forensic-shaped questions in this benchmark. It does
  **not** mean any hybrid implementation will win in any domain.
- The eval set is committed so anyone can extend it, attack it, or
  rebut it. That is the point.

## What would strengthen the benchmark

- More cases sampled from public forensic write-ups.
- LLM-as-judge scoring layered on top of the deterministic checks.
- A reranker and stronger embedding models on top of the vector-RAG
  baseline.
- A real GraphRAG implementation as a stronger comparison.
- Inter-rater agreement on the `expected_best_method` labels.

The project deliberately ships the simpler baselines instead so the
numbers can be reproduced on a clean clone in mock mode without any
API keys.
