# LLM Wiki vs RAG vs GraphRAG

Four answer providers ship with this project. Each is good at a
different thing. The table below summarises the trade-offs; the
forensic examples come from `case_002_evolving`.

## Comparison table

| Method | Primary artifact | Best at | Weakness | Forensic example |
|---|---|---|---|---|
| **Raw RAG** | Lexical index over `raw_sources/` | Simple lookups; answering from a single line that already says the answer | No synthesis, no contradictions, no refusal discipline | *"What does the Defender scan say?"* → returns `Threats Found: 0` |
| **GraphRAG-lite** | Derived node/edge graph at `.fw/graph.json` | Relationship retrieval; entity enumeration; one- and multi-hop walks | No confidence, no contradictions, no investigation state | *"What is DeskRest.exe related to?"* → enumerates `powershell_history.txt`, the Run-key registry key, `203.0.113.77`, the Defender source, the hash-reputation source |
| **LLM Wiki** | Maintained markdown pages + `.fw/{state,events,claims}.json` | Current assessment; refusal of unsupported claims; reconciliation across sources; report drafting | Slower than retrieval on lookups; assessment depends on the wiki being kept up to date | *"Is this confirmed malware?"* → *"No. Malware is not confirmed."* with `claim_NNNN` evidence and explicit contradictions |
| **Hybrid Wiki + Graph** | Wiki answer with graph relationship context appended | Combining synthesis (wiki) with structural context (graph) | Output is longer; same upkeep cost as the wiki | *"Explain the evidence chain and current assessment for DeskRest.exe."* → wiki assessment + relationship footer in a single answer |

## Scoring summary on `case_002_evolving`

From `benchmark_results/case_002_evolving/method_comparison.md`, on a
23-question methods eval covering eight categories:

| Metric | Raw RAG | GraphRAG-lite | LLM Wiki | Hybrid |
|---|---:|---:|---:|---:|
| Passed | 7 / 23 | 5 / 23 | 19 / 23 | **20 / 23** |
| Missing source failures | 15 | 20 | 2 | **2** |
| Contradiction misses | 2 | 2 | 0 | **0** |
| Relationship coverage | 0.60 | 0.60 | 0.80 | **1.00** |
| Narrative state quality | 0.14 | 0.00 | 0.71 | **0.71** |
| Refusal accuracy | 0.33 | 0.00 | 0.75 | **0.75** |
| Expected-best wins | 0 | 2 | **14** | 3 |

In the 23-question method benchmark, Hybrid passed **20 / 23**, LLM Wiki
passed **19 / 23**, Raw RAG passed **7 / 23**, and GraphRAG-lite passed
**5 / 23**. GraphRAG-lite performed best on its intended niche
(relationship questions). LLM Wiki performed better on contradiction
tracking, refusal, and current investigation assessment. Hybrid
performed best overall. These results are scoped to this synthetic
benchmark — see `docs/threats_to_validity.md`.

## When to pick which

- **Raw RAG** when the answer is a single line that already lives
  verbatim in a raw source.
- **GraphRAG-lite** when the question is about how entities connect to
  each other and you don't need a confidence rating or refusal
  behaviour.
- **LLM Wiki** when the answer requires reconciling sources, stating an
  assessment, refusing an unsupported claim, or drafting a report.
- **Hybrid** when you want both. In practice this is the right default
  for forensic walkthroughs and demos.

## What this benchmark deliberately does not do

- It does not call an LLM-as-judge. Scoring is fully deterministic
  substring / refusal checks on the rendered answers.
- It does not invent numbers. Every cell in the table above is
  reproducible with `python fw.py benchmark-methods case_002_evolving`
  from a clean clone.
- It does not cherry-pick questions. The eval covers eight categories,
  every category has at least two questions, and the
  `expected_best_method` column on every row tells you up front which
  provider the question was designed to favour.

## See also

- `docs/why_llm_wiki.md` — the "why bother" pitch in one document.
- `docs/architecture.md` — three layers, four verbs, Mermaid diagram.
- `docs/rag_vs_llm_wiki.md` — two-way comparison (Raw RAG vs LLM Wiki)
  with worked examples.
- `docs/benchmark_methodology.md` — exactly how scoring works.
- `docs/threats_to_validity.md` — what these results do and do not
  generalise to.
- `PROJECT_SUMMARY.md` — recruiter-friendly one-pager.
