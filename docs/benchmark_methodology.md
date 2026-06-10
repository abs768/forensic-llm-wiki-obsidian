# Benchmark methodology

Scope: this document describes exactly how `fw.py benchmark` scores
answers. The scoring is deterministic and small. There is no
LLM-as-judge.

## What is scored

For every question in `evals/<case_id>_eval.json`, two providers answer:

1. **LLM Wiki** — `query.answer_question()` against the compiled wiki.
2. **Raw RAG** — `rag.rag_query()`, a BM25-ish lexical search over
   `raw_sources/<case_id>/`.

Both answers are run through the **same** check pipeline. Whatever the
wiki gets credit for, the baseline also gets credit for — and vice
versa.

## The checks

Every eval item declares these expectations. Empty lists mean the check
does not apply.

### `must_include: [str, ...]`

Each term must appear as a substring (case-insensitive) in the rendered
answer text. The rendered text includes the `Sources:` section, so
required file citations are checked here too.

A miss is one **failed check** and does not have its own counter unless
it was a source basename (see below).

### `must_not_include: [str, ...]`

Each term must **not** appear in the answer text. A hit is one failed
check **and** increments the **`unsupported_claim_failures`** counter.
The terms in the eval are deliberately the phrases the wiki must refuse:
"confirmed malware", "data was stolen", "exfiltration occurred", etc.

### `required_sources: [str, ...]`

Each entry is matched on its **basename** against the answer text. A
miss is one failed check **and** increments the **`missing_source_failures`**
counter. Sources are checked against the rendered answer, so the `Sources:`
section produced by `format_answer` is the primary surface.

### `expect_refusal: bool`

If true, the answer must refuse the claim. The refusal heuristic is
deliberately strict: the answer must either be the literal
"insufficient evidence" sentence, or contain "not confirmed", or
begin with "Answer:\nNo." (or another "no"-prefixed line).

If the answer does **not** refuse when refusal was expected, the
`expect_refusal` check fails and the question contributes to the
`refusal_accuracy` denominator without contributing to the numerator.

### `expect_separation: bool`

If true, the answer must separate facts from hypotheses. This holds if
the answer is classified as `hypothesis`, **or** the rendered text
contains both "fact" and "hypothesis" (case-insensitive).

## Derived metrics

These appear in `benchmark_results/<case>/results.md`:

- **Total questions** — count of eval items in the case file.
- **Passed / Failed** — per-provider counts. A question passes only if
  every applicable check passes.
- **Unsupported claim failures** — sum of `must_not_include` violations
  per provider.
- **Missing source failures** — sum of `required_sources` misses per
  provider.
- **Contradiction misses** — count of `contradiction_detection`-category
  questions the provider failed. (Wiki should win this consistently;
  RAG has no contradictions ledger.)
- **Refusal accuracy** — fraction in `[0, 1]` of questions with
  `expect_refusal: true` where the provider actually refused.

## Honest caveats

- **Synthetic case set.** The two demo cases are scripted for
  demonstration; they are not representative of arbitrary real
  incidents.
- **Small N.** The included eval is 16 questions for the evolving case
  and 4 for case_001. Conclusions about "wiki beats RAG" should be
  read as a worked example, not a statistical claim across a population
  of cases.
- **Mock LLM.** All scoring runs the mock provider. The mock pipeline
  is deterministic; a real LLM is likely to be **more** capable than
  the mock for some questions and **less** consistent for others.
- **Deterministic scoring is shallow.** Substring matching cannot
  distinguish a properly-cited "not confirmed" answer from a
  scrambled one that happens to contain the right tokens. A real
  evaluation suite would add LLM-as-judge or human review; this
  project deliberately ships without that to keep the demo
  reproducible.

## Reproducing the numbers

```bash
python fw.py evolve case_002_evolving      # ingest all 6 steps cleanly
python fw.py benchmark case_002_evolving   # writes results.md + results.json
```

Outputs land under `benchmark_results/<case>/`. Both files are
committed to the repo for case_002_evolving so reviewers can see the
numbers without running the code.
