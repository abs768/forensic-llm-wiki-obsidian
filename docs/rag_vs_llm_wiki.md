# RAG vs LLM Wiki

This document contrasts the three retrieval/synthesis modes this project
can produce, using the included `case_002_evolving` demo as the worked
example.

## The three modes

### Raw-source retrieval (`rag-query`)

Pure lexical search over `raw_sources/`. The project ships a small
BM25-ish scorer in `src/rag.py`. For each question:

1. Tokenise.
2. Score every raw file's lines.
3. Return the top few snippets with their file paths.

There is **no synthesis**. The answer is a faithful list of the
highest-scoring snippets that match the query terms.

### Compiled wiki querying (`query`)

Reads the **compiled** wiki state, not the raw sources. The wiki state
is the result of every prior `ingest`:

- Entities deduped by canonical key.
- Events ordered chronologically.
- Hypotheses with separated facts / inferences / supporting /
  contradicting evidence, plus a confidence rating.
- Contradictions as first-class entries that link the conflicting
  claims.

The answer composes claims, events, and contradictions into the
`Answer / Assessment / Evidence / Contradictions / Confidence / Sources`
layout. If the wiki has nothing to say on a topic, it falls back to the
raw-source baseline **with a visible note** so the reader knows.

### Hybrid evidence lookup (used by `compare` and `benchmark`)

The `compare` command runs both `query` and `rag-query` against the same
question and prints them side by side. The `benchmark` command does the
same across the whole eval set and scores each provider on the same
deterministic checks.

The point is honesty: the project does not hide the raw-source baseline,
it scores against it.

## Why the wiki wins on the demo case

### Question 1 — "Is this confirmed malware?"

**Raw RAG**:

> Based on `raw_sources/` keyword hits, the most relevant line is:
>
> > Initial triage by analyst Bob suggests possible malware infection.
>
> (No reconciliation with the Defender clean scan, no mention of the
> inconclusive hash reputation, no confidence rating.)

**LLM Wiki**:

> No. Malware is not confirmed. The wiki supports suspicious behaviour
> and possible persistence, but does not escalate any hypothesis to High
> or Confirmed.
>
> Evidence:
> - claim_0001 Possible Outbound C2 Beacon (Low)
> - claim_0002 Possible Registry-Based Persistence (Medium)
> - claim_0003 Suspicious Process Execution Chain (Medium)
>
> Contradictions / caveats:
> - Suspicious activity vs. clean AV scan — Defender reported 0 threats.
> - Investigator suspicion vs. limited objective evidence — diagnosis
>   remains Medium.
> - Investigator malware suspicion vs. inconclusive hash reputation —
>   verdict "Unknown".
>
> Confidence: Medium (hypothesis)

The wiki refuses; RAG cannot.

### Question 2 — "What evidence supports persistence?"

**Raw RAG**: returns the literal Run-key line from `registry_run_keys.reg`.
That happens to be a correct fact.

**LLM Wiki**: returns the persistence hypothesis (`claim_0002`), the
fact bullets that back it, the citation to the .reg file, the active
contradiction (the clean Defender scan), and the open questions
(signing? hash reputation?).

Both answer the question, but only one tells the analyst what to do
next.

### Question 3 — "What changed after the Defender scan was added?"

**Raw RAG**: cannot meaningfully answer. It has no notion of "before"
and "after"; every query starts from scratch over the same corpus.

**LLM Wiki**: `diff-snapshots after_step_02_registry after_step_03_defender`
shows the exact markdown that changed — the wiki softened its assessment
and added the AV-vs-suspicion contradiction.

## The numbers

From `benchmark_results/case_002_evolving/results.md`, on the 16-question
eval set:

| Metric | Raw RAG | LLM Wiki |
|---|---:|---:|
| Passed | 4 / 16 | 16 / 16 |
| Unsupported claim failures | 0 | 0 |
| Missing source failures | 14 | 0 |
| Contradiction misses | 2 | 0 |
| Refusal accuracy | 0.33 | 1.00 |

The wiki is not magically better at retrieval — it is better at
**accumulating** retrieval. Every prior `ingest` is doing the
synthesis work that naive RAG would otherwise have to redo on every
question.

## When RAG is the right tool

If you need an unambiguous local fact ("what's our return policy?",
"what is the SHA-256 hash listed on line 7?"), naive RAG is
fine. You don't need a hypothesis ledger to look up a single line.

The LLM Wiki pattern earns its keep when the answer is **synthesised
across many sources**, **must reconcile contradictions**, or **must
refuse unsupported conclusions**. Forensic investigation is one such
domain. Pure RAG drops the ball there in ways the benchmark makes
unmissable.
