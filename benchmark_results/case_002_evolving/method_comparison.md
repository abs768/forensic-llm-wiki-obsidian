# Method Comparison — `case_002_evolving`

Four providers were scored against the same eval set:

1. **Raw RAG** — naive BM25 over raw_sources/.
2. **GraphRAG-lite** — answers from the derived relationship graph.
3. **LLM Wiki** — answers from the compiled investigation state.
4. **Hybrid** — wiki assessment + graph relationship context.

## Scoring summary

| Metric | Raw RAG | GraphRAG-lite | LLM Wiki | Hybrid |
|---|---:|---:|---:|---:|
| Total questions | 23 | 23 | 23 | 23 |
| Passed | 7 | 5 | 19 | 20 |
| Failed | 16 | 18 | 4 | 3 |
| Unsupported claim failures | 0 | 0 | 0 | 0 |
| Missing source failures | 15 | 20 | 2 | 2 |
| Contradiction misses | 2 | 2 | 0 | 0 |
| Relationship coverage | 0.60 | 0.60 | 0.80 | 1.00 |
| Narrative state quality | 0.14 | 0.00 | 0.71 | 0.71 |
| Refusal accuracy | 0.25 | 0.00 | 0.75 | 0.75 |
| Expected-best wins | 0 | 2 | 14 | 3 |

## Per-question results

| ID | Category | Expected best | Raw RAG | GraphRAG-lite | LLM Wiki | Hybrid |
|---|---|---|:---:|:---:|:---:|:---:|
| lookup_001 | simple_lookup | llm_wiki | PASS | fail | PASS | PASS |
| lookup_002 | simple_lookup | llm_wiki | PASS | PASS | PASS | PASS |
| lookup_003 | simple_lookup | llm_wiki | fail | fail | PASS | PASS |
| rel_001 | relationship_retrieval | graph_rag_lite | PASS | PASS | PASS | PASS |
| rel_002 | relationship_retrieval | graph_rag_lite | fail | fail | PASS | PASS |
| rel_003 | relationship_retrieval | graph_rag_lite | fail | PASS | fail | PASS |
| multihop_001 | multi_hop_relation | hybrid | PASS | fail | PASS | PASS |
| multihop_002 | multi_hop_relation | hybrid | PASS | PASS | PASS | PASS |
| contra_001 | contradiction_detection | llm_wiki | fail | fail | PASS | PASS |
| contra_002 | contradiction_detection | llm_wiki | fail | PASS | PASS | PASS |
| contra_003 | contradiction_detection | llm_wiki | PASS | fail | PASS | PASS |
| refuse_001 | unsupported_claim_refusal | llm_wiki | fail | fail | PASS | PASS |
| refuse_002 | unsupported_claim_refusal | llm_wiki | fail | fail | PASS | PASS |
| refuse_003 | unsupported_claim_refusal | llm_wiki | fail | fail | PASS | PASS |
| state_001 | current_investigation_assessment | llm_wiki | fail | fail | PASS | PASS |
| state_002 | current_investigation_assessment | llm_wiki | fail | fail | PASS | PASS |
| state_003 | current_investigation_assessment | llm_wiki | fail | fail | PASS | PASS |
| evol_001 | hypothesis_evolution | llm_wiki | PASS | fail | PASS | PASS |
| evol_002 | hypothesis_evolution | llm_wiki | fail | fail | PASS | PASS |
| report_001 | final_report_accuracy | llm_wiki | fail | fail | fail | fail |
| report_002 | final_report_accuracy | llm_wiki | fail | fail | fail | fail |
| hybrid_001 | hybrid | hybrid | fail | fail | fail | fail |
| hybrid_002 | hybrid | hybrid | fail | fail | PASS | PASS |

## What to read out of this table

- **Relationship coverage** should favour GraphRAG-lite (and Hybrid, which inherits it).
- **Narrative state quality**, **refusal accuracy**, and **contradiction misses** should favour LLM Wiki and Hybrid.
- **Hybrid** should win the most ``expected_best`` wins because it has both the graph context and the wiki's assessment.
- Raw RAG is the foil. It is included to make the cost of 'just retrieve' visible.
