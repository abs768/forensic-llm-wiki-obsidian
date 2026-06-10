# Forensic LLM Wiki Case Study

A markdown-first AI investigation system that compiles raw forensic
evidence into an evolving, citation-backed case wiki — and a
deterministic benchmark that compares it against a raw lexical RAG
baseline, a GraphRAG-lite relationship-graph baseline, and a Hybrid
that combines both.

> **RAG retrieves. GraphRAG relates. LLM Wiki maintains evolving
> case state. Hybrid combines them.**

## Problem

Retrieval-Augmented Generation treats every question as a cold-start
search over the raw corpus. For investigation-shaped work —
forensics, incident response, research synthesis — that approach is
structurally insufficient. There is no place for accumulated
hypotheses, no contradictions ledger, and no discipline that forces
the system to refuse claims the evidence does not support. A loud
analyst note saying *"confirmed malware"* drowns out a quiet AV clean
scan in the same corpus. The result is confidently wrong answers.

Real cases need persistent state — timelines, entities, IOCs,
hypotheses with separated facts / inferences / supporting / contradicting
evidence, an explicit contradictions ledger, open questions, and a
report draft. Retrieval alone cannot maintain any of that.

## Why raw RAG is insufficient

The project ships a small BM25-style lexical baseline (`fw.py rag-query`)
as a foil. On the included `case_002_evolving` benchmark, asked
*"Is this confirmed malware?"*:

- Raw RAG retrieves the analyst's *"possible malware infection"* line.
- It cannot reconcile that against the Defender clean scan from the
  same corpus.
- It has no notion of confidence, no contradictions ledger, no refusal
  discipline.

The baseline is deliberately simple. Even a vector-RAG with embeddings
would still lack the synthesis layer; the gap on synthesis / refusal
questions is structural, not a retrieval-quality artefact.

## Why GraphRAG alone is not enough

The project also ships a deterministic **GraphRAG-lite** baseline
(`src/graph/`) that derives a relationship graph from the wiki's
existing structured indexes. It is honest about being a local graph,
not Microsoft GraphRAG. It is good at:

- *"What is DeskRest.exe related to?"* — walks the graph and lists
  neighbours.
- *"What is connected to the registry Run key?"* — answers cleanly.

It is weak at:

- *"Is this confirmed malware?"* — the graph has no confidence, no
  refusal behaviour, no contradictions ledger.
- *"How did the assessment change after the Defender scan arrived?"*
  — the graph has no time dimension.

> **GraphRAG answers:** *"What is connected to what?"*
> **LLM Wiki answers:** *"What do we currently believe, why, what
> contradicts it, and how did that belief change?"*

## Architecture

Three on-disk layers, four core CLI verbs, no database.

```
raw_sources/       immutable evidence (LLM may read, never write)
       │ ingest
schema/            page templates + citation rules + lint rules
       │ controls
wiki/cases/<id>/   markdown investigation state
                   index, timeline, entities, iocs,
                   hypotheses, contradictions,
                   open_questions, final_report
                   .fw/   state.json, manifest.json,
                          events.json, entities.json, claims.json,
                          traces.jsonl, ingestion_log.jsonl,
                          hypothesis_history.json, graph.json,
                          review_queue/, review_history.jsonl
       │
query · lint · report · benchmark · evolve · graph-* · compare-all ·
review · export-obsidian · MCP server
```

- **Markdown is the product.** Every page is human-readable and
  re-rendered from a structured snapshot on every ingest, so markdown
  and state cannot drift.
- **Stable IDs.** Every event, entity, and hypothesis gets
  `evt_NNNN` / `ent_NNNN` / `claim_NNNN` that survives re-ingest.
- **Schema-governed.** `schema/{wiki_schema, page_templates,
  citation_rules, lint_rules}.md` defines what a "good" wiki page
  looks like and what lint flags.
- **Pydantic boundary.** The LLM proposes structured updates; the
  orchestrator validates them; the renderer writes markdown. Invalid
  structures cannot reach disk.
- **MCP server** exposes 13 tools so any MCP-aware client can list
  cases, read pages safely (path-traversal blocked), ingest, query,
  lint, generate the report, compare methods, walk the relationship
  graph, and pull hypothesis history / contradictions / open questions.
- **Human review queue** holds risky updates (*confirmed malware*,
  *exfiltration occurred*, …) until a human approves or rejects them,
  with every decision appended to `.fw/review_history.jsonl`.

## Case evolution benchmark

`raw_sources/case_002_evolving/` ships six step subdirectories
(`step_01_powershell` → `step_06_hash_reputation`), one evidence drop
per step. `fw.py evolve <case>` ingests each step in order, snapshots
the wiki between steps, runs eval + lint, captures a key-question
assessment per step, and updates `.fw/hypothesis_history.json`.

On the six-step synthetic evolving forensic case, the LLM Wiki query
path passed **16 / 16** deterministic eval checks while the raw lexical
RAG baseline passed **4 / 16**. Refusal accuracy was **1.00** for LLM
Wiki vs **0.33** for raw RAG. The per-step eval climbs monotonically as
evidence arrives:

```
step_01_powershell        eval 2 / 16
step_02_registry          eval 2 / 16
step_03_defender          eval 5 / 16
step_04_network           eval 8 / 16
step_05_investigator_note eval 11 / 16
step_06_hash_reputation   eval 16 / 16
```

`fw.py diff-snapshots case_002_evolving after_step_02_registry
after_step_03_defender` shows the literal moment the wiki softens its
assessment after the Defender clean scan lands.

In the 23-question method benchmark on the same case, **Hybrid passed
20 / 23, LLM Wiki passed 19 / 23, Raw RAG passed 7 / 23, and
GraphRAG-lite passed 5 / 23.** GraphRAG-lite performed best on its
intended niche — relationship questions. LLM Wiki performed better on
contradiction tracking, refusal, and current investigation
assessment. Hybrid performed best overall. These results are scoped
to this synthetic benchmark and should not be read as a universal
claim about RAG or GraphRAG — see
`docs/threats_to_validity.md`.

## Adversarial overclaim test

`case_003_adversarial_overclaim` is a deliberate stress test: the
investigator notes assert *"confirmed malware"*, *"data was
exfiltrated"*, and *"the attacker stole files"* — three explicit
overclaims the wiki must refuse to endorse.

In the adversarial overclaim case, where analyst notes asserted
*"confirmed malware"* and *"data was exfiltrated"* without sufficient
supporting evidence, the wiki path passed **11 / 11** deterministic
checks while raw RAG passed **2 / 11**.

The wiki:

- Refuses each overclaim explicitly (*"Malware is not confirmed."*).
- Surfaces the Defender clean scan and the inconclusive hash
  reputation as contradicting evidence to the analyst's claim.
- Quotes the investigator's overclaim faithfully on the timeline (as
  an analyst claim, with attribution) without itself asserting it.
- Routes *"what contradicts the malware hypothesis?"* through the
  confirmation answer builder so the contradictions ledger is what
  gets surfaced, not the loudest matching raw line.

This is the central piece of evidence that schema rules + lint + the
contradictions ledger work together. The wiki does not launder an
analyst's overclaim.

## AI engineering decisions

- **The LLM is not allowed to write files directly.** Extraction
  returns Pydantic-validated `ExtractedFacts`; the orchestrator
  merges; the renderer writes markdown.
- **Raw sources are immutable.** `raw_sources/` is the only
  ground-truth layer. Every fact in the wiki cites back to it.
- **The markdown wiki is the compiled knowledge layer.** Sidecar JSON
  in `.fw/` exists to make queries fast and lint rigorous, not to
  replace markdown.
- **Schema controls page structure and lint rules.** Required pages,
  citation rules, and lint severity tiers all live in `schema/*.md`.
- **Facts / inferences / hypotheses / contradictions are separated.**
  Hypothesis pages enforce a five-subsection template. Confidence is
  declared, not implied.
- **Unsupported claims are refused or linted.** Four severity tiers.
  Critical findings include unattributed *"confirmed malware"*,
  *"exfiltration occurred"*, broken raw-source citations, and
  final-report claim IDs that don't exist in `.fw/claims.json`.
- **Adversarial overclaim case** specifically tests blind trust in
  analyst notes. It is in the repo precisely so a reader can confirm
  the wiki refuses each overclaim.
- **Deterministic mock mode** keeps tests reproducible without API
  keys. The mock pipeline runs the same parser / extractor code path a
  live LLM would post-process; the wiki it produces is honest, not a
  stub.
- **Benchmarks are deterministic, not LLM-as-judge.** Substring
  `must_include` / `must_not_include`, basename `required_sources`
  checks, refusal heuristic, and category-bucketed scoring. The
  scorecards are reproducible from a clean clone.
- **MCP exposes tools for agent-native workflows.** 13 tools. The
  agent uses the wiki as maintained working memory, not as raw
  document search.
- **Human review catches risky forensic conclusions.** `--review`
  routes risky pages into `.fw/review_queue/` with a full audit trail
  in `.fw/review_history.jsonl`.

## Software engineering decisions

- **Modular file-based architecture.** `fw.py` is a thin CLI
  dispatcher. Each subcommand calls a function in `src/<op>.py`. The
  same functions back the MCP tools.
- **No unnecessary infrastructure.** No FastAPI, no database, no
  vector store, no frontend, no LangChain, no Neo4j. Listed as
  explicit non-goals in `CONTRIBUTING.md`.
- **Incremental ingestion with manifest and source hashes.** Unchanged
  files are skipped by default; `--force` reprocesses everything;
  `--dry-run` previews unified diffs without writing.
- **Stable IDs for events / entities / claims** across re-ingest so
  citations from the final report don't break.
- **196 tests** across 17 files, all in mock mode. `pytest` runs in
  ~6 s. **Ruff clean.** **CI on Python 3.11 and 3.12** via GitHub
  Actions: `ruff check`, `pytest`, plus a smoke test of the demo flow.
- **Path traversal blocked.** The MCP `read_wiki_page` tool resolves
  paths against the case dir and refuses anything that escapes it.
  The `.fw/` sidecar is sealed off from MCP reads.
- **Audit trail.** Every operation appends to `.fw/traces.jsonl`. Every
  review decision appends to `.fw/review_history.jsonl`. Every ingest
  appends to `.fw/ingestion_log.jsonl`.
- **Reproducible demo and benchmark commands.** `examples/demo_commands.sh`
  runs end-to-end; benchmark scorecards are committed; `make
  launch-check` is the single command that gates a release.
- **Sidecar protected from MCP reads.** Agents see markdown, not
  internal state.

## What was hard

> The hard part was not generating markdown. The hard part was
> maintaining citation discipline, separating facts from hypotheses,
> and preventing overconfident forensic conclusions as evidence
> arrived incrementally.

Specific friction points:

1. **Attributed quotation vs. assertion.** A naive lint pass would
   flag *"investigator note: confirmed malware"* because it contains
   the phrase, even though the wiki was *quoting* the analyst, not
   asserting. The fix is an attribution-aware check in
   `_check_unsupported_confirmation`. The same logic is reused by the
   review-queue risky-phrase scanner.
2. **Verbatim echo in generic answers.** A naive `_answer_generic`
   would surface the matching event whose description literally
   contained *"confirmed malware"* — turning the wiki's own answer
   into an unattributed overclaim. The fix is a risky-phrase filter
   on event descriptions before they reach `evidence_items`, plus a
   contradiction-question router that prefers the confirmation answer
   builder.
3. **Stable IDs across re-ingest.** Adding new hypotheses must not
   renumber existing ones, because `claim_NNNN` references in
   `final_report.md` would break. The fix is a per-kind counter and
   fingerprint map in `WikiState`. Lint rule H4 verifies that every
   `claim_NNNN` in the final report still exists in
   `.fw/claims.json`.
4. **Two-pass contradiction detection.** A clean Defender scan can
   only become a contradiction *after* a persistence hypothesis is in
   the wiki. The ingest loop runs extraction in pass one and
   contradiction detection in pass two, so file ordering does not
   change the outcome.
5. **Backwards-compatible refactors.** The state file moved from
   `_state.json` to `.fw/state.json` in Phase 2; the loader still
   picks up the legacy location and migrates transparently so existing
   wikis don't break.
6. **Mock vs live divergence.** The mock pipeline uses deterministic
   rule-based extractors that run *the same code path* a live LLM
   would post-process. That keeps tests reproducible without an API
   key while still exercising the real merge / render / lint logic.

## Limitations

- The benchmark is synthetic and small. Three demo cases, around 50
  eval questions total. Read the numbers as architecture evidence,
  not as universal proof.
- The raw-RAG baseline is lexical (BM25-style), not vector. A real
  vector-RAG with embeddings would do better on some questions — but
  the gap on synthesis / refusal questions is structural.
- GraphRAG-lite is a deterministic local graph baseline, not Microsoft
  GraphRAG. Cluster summaries and community detection are not
  implemented.
- Deterministic mock mode is used for tests and CI. Real LLM
  behaviour will differ; the numbers in this case study are
  mock-mode results.
- No LLM-as-judge in benchmarks. Scoring is substring + refusal +
  category checks.
- No EVTX / MFT / prefetch / PCAP parsers yet. The file kinds in
  `parsers.py` are representative samples.
- No production security sandbox. Treat live-mode inputs as
  untrusted.
- No multi-user access control. The CLI and MCP server trust their
  caller.
- The risky-phrase detector is substring-based with an attribution
  override; novel paraphrases would slip through without a schema
  update.
- **Not a malware verdict engine.** The wiki refuses confirmed-malware
  language unless backed by High-confidence hypotheses with multiple
  supporting bullets.
- See `docs/threats_to_validity.md` for the long form.

## Future work

- LLM-as-judge scoring layered on top of the deterministic checks.
- More demo cases sampled from public forensic write-ups.
- A real vector-RAG baseline (embeddings + reranker).
- A real GraphRAG implementation as a third comparison.
- Local-model mode (Ollama, llama.cpp) for air-gapped use.
- Richer forensic parsers: EVTX, MFT, prefetch, PCAP.
- An Obsidian plugin for in-place ingest.
- Multi-reviewer queue with role-based approval.

## Reproducing the results

```bash
git clone <repo> && cd forensic-llm-wiki
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                                             # 196 tests, mock mode
ruff check .
python fw.py evolve case_002_evolving              # eval climbs 2 → 16
python fw.py benchmark case_002_evolving           # two-way scorecard
python fw.py benchmark-methods case_002_evolving   # four-way scorecard
python fw.py ingest raw_sources/case_003_adversarial_overclaim --apply
python fw.py benchmark case_003_adversarial_overclaim
python fw.py compare-all case_002_evolving "Is this confirmed malware?"
```

No API key is required for any of the above.
