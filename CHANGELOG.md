# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

[0.4.0]: https://github.com/abs768/forensic-llm-wiki-obsidian/releases/tag/v0.4.0
