# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- First recorded live-LLM smoke test (`examples/live_runs/`): full run
  against `claude-sonnet-4-6` on the evolving and adversarial cases.
  Refusal discipline, analyst-claim attribution, and the contradictions
  ledger all held with a real model in the loop.

### Fixed

- Live ingest no longer crashes when the model returns entity/IOC types
  outside the schema vocabulary: the extraction prompt now enumerates
  the allowed types, and `normalize_llm_types()` coerces any remaining
  unknown labels to `other` with a note recording the original label.
  Found by the live smoke test on its first API call.

## [0.5.0] — 2026-07-08

### Added

- **Vector-RAG baseline** (`src/vector_rag.py`): embedding retrieval with
  cosine top-k over chunked raw sources, as a stronger control against the
  lexical baseline. Real runs use `sentence-transformers/all-MiniLM-L6-v2`
  (`pip install -e ".[vector]"`, `FORENSIC_WIKI_EMBEDDINGS=local`); tests
  and CI use a deterministic hashed bag-of-words embedder with no model
  download. New `vector-query` CLI command; `compare-all` and
  `benchmark-methods` are now five-way. The committed
  `case_002_evolving` scorecard was regenerated with real embeddings:
  Vector RAG passes 10/23 (Raw RAG 7/23) but the refusal and
  narrative-state gaps against the maintained wiki persist.

- Coverage reporting in CI with an enforced 85% line-coverage floor
  (currently at 91%).
- Mypy type checking in CI; the codebase is mypy-clean.
- Pre-commit configuration (`ruff check`, whitespace and file hygiene hooks).
- `make coverage` and `make typecheck` targets; `make launch-check` now also
  runs mypy and the coverage floor.
- Terminal demo GIF and Obsidian graph-view screenshot in the README.

### Fixed

- Fourteen type errors surfaced by mypy: loop-variable shadowing in
  `ingest`, `report`, `evolve`, and `entity_extractor`; missing `None`
  narrowing in `claim_extractor`; and over-wide `str` types where the
  schemas expect literal types (`manifest`, `query`, `fw`, `tracing`).

## [0.4.0] — 2026-07-07

First public release. Versions before 0.4.0 were internal iterations and were
never published.

### Added

- **Ingest pipeline**: compiles raw forensic evidence into a markdown
  investigation wiki with structured `.fw/` sidecar indexes (events, entities,
  claims). Incremental via a SHA-256 manifest, with `--dry-run`, `--force`,
  and `--review` modes.
- **Query engine**: answers from the compiled wiki with citations, plus a raw
  lexical RAG baseline (`rag-query`) and side-by-side `compare`.
- **GraphRAG-lite baseline**: deterministic local entity graph with
  `graph-build`, `graph-query`, and Mermaid export.
- **Four-way benchmark**: Raw RAG vs GraphRAG-lite vs LLM Wiki vs Hybrid with
  deterministic scoring (no LLM-as-judge). Committed scorecards under
  `benchmark_results/`.
- **Evolving case support**: `evolve` replays six staged evidence drops;
  `diff-snapshots` diffs investigation state between steps.
- **Adversarial overclaim case**: verifies the wiki refuses analyst
  conclusions the evidence does not support.
- **Human review queue**: risky conclusions (e.g. "confirmed malware") are
  routed to `.fw/review_queue/` for approve/reject instead of landing in the
  wiki automatically.
- **MCP server**: 13 tools exposing query, lint, report, graph, review, and
  case-summary operations to agents, with path-traversal protection.
- **Obsidian export**: clean vault with wiki links, Mermaid graph, and an
  orientation README.
- **Lint rules**: citation discipline, unsupported-claim detection, JSON
  output for CI.
- Test suite (mock LLM mode, no API key required), Ruff linting, and CI on
  Python 3.11 and 3.12.

[0.5.0]: https://github.com/abs768/forensic-llm-wiki-obsidian/releases/tag/v0.5.0
[0.4.0]: https://github.com/abs768/forensic-llm-wiki-obsidian/releases/tag/v0.4.0
