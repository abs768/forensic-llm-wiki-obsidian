# Contributing

Thanks for your interest. The project is small, deliberate, and easy to
extend, but it has strong opinions about what it is and what it is not.
Please read this whole document before opening a PR.

## What kinds of contributions are welcome

- **Bug fixes**, especially around ingest correctness, lint accuracy,
  and the wiki-vs-RAG benchmark scoring.
- **New parsers** in `src/parsers.py` for additional forensic file kinds
  (EVTX, MFT, prefetch, PCAP, Sysmon XML, etc.). Each new parser
  should come with corresponding entries in `src/entity_extractor.py`
  and `src/claim_extractor.py`, plus tests.
- **New lint rules** in `src/lint.py`. Update `schema/lint_rules.md` to
  document them.
- **More demo cases** under `raw_sources/<case>/` with matching evals
  under `evals/<case>_eval.json`.
- **Documentation** — examples, tutorials, screen recordings.

## What kinds of contributions are out of scope (for now)

These are intentional non-goals for the current project. A PR that adds
any of them will likely be closed with a thank-you:

- **A backend** (FastAPI, Flask, etc.). The CLI is the product.
- **A frontend** (React, Vue, etc.).
- **A database** (Postgres, SQLite, Mongo, …). Markdown is the store.
- **A vector store** (pgvector, Chroma, Qdrant, …). Lexical RAG ships
  as a *foil*, not a replacement.
- **LangChain / LlamaIndex** as the implementation framework.
- **A graph database** (Neo4j, …). Wiki links serve the same purpose.
- **LLM-as-judge** in the benchmark. Scoring stays deterministic.

If you have a strong case for any of the above, please open an issue
first and we can discuss.

## Style and conventions

- **Python 3.11+**, type-hinted where reasonable.
- **Pydantic** for every structured object the LLM or the user-facing
  CLI produces. Invalid structures must not reach disk.
- **Markdown is the user-facing layer.** Sidecar JSON in `.fw/` exists
  to make queries fast and lint rigorous, not to replace markdown.
- **No file I/O in pure logic functions.** Read/write happens in
  `src/wiki_io.py`, `src/manifest.py`, `src/tracing.py`,
  `src/snapshots.py`. Other modules return data structures.
- **Cite everything.** Every fact in the wiki must carry either a
  `Source: raw_sources/...` citation or a `claim_NNNN` / `evt_NNNN` /
  `ent_NNNN` reference. Lint enforces this.

## How to run the project locally

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"          # editable install with ruff + pytest
make demo                         # full end-to-end script
```

## How to run the test suite

```bash
make test         # pytest
make lint         # ruff check
make format       # ruff format
```

The whole test suite must pass in mock-LLM mode. Do not introduce tests
that require network access or a real Anthropic API key.

## How to add a new parser + extractor

1. Pick a stable file extension or filename pattern.
2. Add a kind to `SourceKind` in `src/parsers.py` and update
   `detect_kind` + (if structured) the relevant `_parse_*` helper.
3. Add an entity extraction branch in
   `src/entity_extractor.py::extract_entities`.
4. Add events / IOCs / hypotheses / contradictions in the corresponding
   branches of `src/claim_extractor.py`.
5. Drop a representative sample file under
   `raw_sources/case_xxx_yourcase/` plus an eval under
   `evals/case_xxx_yourcase_eval.json`.
6. Write tests under `tests/` covering both the parser and the
   extractor.

## How to propose a new lint rule

1. Document it in `schema/lint_rules.md` with severity and rationale.
2. Implement the check in `src/lint.py`. Name it `_check_<short_name>`.
3. Wire it from `lint_case`.
4. Add at least one test that asserts the rule fires on a constructed
   failure case **and** one that asserts it does not fire on the clean
   demo case (post-ingest).

## Pull request checklist

- [ ] `pytest` passes (90+ tests, mock mode).
- [ ] `ruff check .` is clean.
- [ ] `python fw.py --help` still works and the new command (if any)
      is listed with a useful one-line description.
- [ ] README and relevant `docs/*.md` are updated.
- [ ] No new dependencies on backends, databases, frontends, vector
      stores, or LLM-as-judge frameworks.
- [ ] If a new file kind: a sample file under `raw_sources/` and at
      least one matching eval question.

Thank you for keeping the project lean.
