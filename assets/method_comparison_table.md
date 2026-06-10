# Method comparison table

| Method | Best at | Weak at | Forensic example |
|---|---|---|---|
| **Raw RAG** | Direct lookup; answering from a single line that already says the answer | No persistent case state, no contradictions ledger, no refusal discipline | *"What does the Defender scan say?"* → returns `Threats Found: 0` cleanly |
| **GraphRAG-lite** | Entity relationships; one- and multi-hop walks | Weak on current assessment / refusal / contradiction reconciliation | *"What is DeskRest.exe related to?"* → enumerates registry, network, AV source files |
| **LLM Wiki** | Hypotheses, contradictions, evolving state, refusal discipline | Requires schema and lint discipline; slower than retrieval on lookups | *"Is this confirmed malware?"* → *"No. Malware is not confirmed."* with `claim_NNNN` evidence + Defender contradiction |
| **Hybrid** | Best overall — wiki narrative state + graph relationship context | More moving parts than any single component | *"Explain the evidence chain and current assessment for DeskRest.exe"* — wiki assessment + graph relationships in one answer |

## Reproduced numbers on `case_002_evolving` (23-question methods eval)

| Metric | Raw RAG | GraphRAG-lite | LLM Wiki | Hybrid |
|---|---:|---:|---:|---:|
| Passed | 7 / 23 | 5 / 23 | 19 / 23 | **20 / 23** |
| Relationship coverage | 0.60 | 0.60 | 0.80 | **1.00** |
| Narrative state quality | 0.14 | 0.00 | 0.71 | **0.71** |
| Refusal accuracy | 0.33 | 0.00 | 0.75 | **0.75** |
| Contradiction misses | 2 | 2 | 0 | **0** |

Read the numbers as architecture evidence, not as universal proof. See
[`docs/threats_to_validity.md`](../docs/threats_to_validity.md) for the
honest limits.

## When to pick which

- **Raw RAG** when the answer is a single line that already lives verbatim
  in a raw source.
- **GraphRAG-lite** when the question is about how entities connect to
  each other and you don't need a confidence rating or refusal behaviour.
- **LLM Wiki** when the answer requires reconciling sources, stating an
  assessment, refusing an unsupported claim, or drafting a report.
- **Hybrid** when you want both. In practice this is the right default
  for forensic walkthroughs and demos.
