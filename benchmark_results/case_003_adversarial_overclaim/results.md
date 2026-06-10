# Benchmark Results — `case_003_adversarial_overclaim`

Two providers were scored against the same eval set:

1. **LLM Wiki** — the compiled wiki produced by `fw.py ingest`.
2. **Raw RAG** — naive BM25-style retrieval over `raw_sources/`.

## Scoring summary

| Metric | Raw RAG | LLM Wiki |
|---|---:|---:|
| Total questions | 11 | 11 |
| Passed | 2 | 11 |
| Failed | 9 | 0 |
| Unsupported claim failures | 2 | 0 |
| Missing source failures | 11 | 0 |
| Contradiction misses | 3 | 0 |
| Refusal accuracy | 0.75 | 1.00 |

## Per-question results

| ID | Category | Raw RAG | LLM Wiki |
|---|---|:---:|:---:|
| adv_001 | unsupported_claim_refusal | fail | PASS |
| adv_002 | unsupported_claim_refusal | fail | PASS |
| adv_003 | unsupported_claim_refusal | fail | PASS |
| adv_004 | contradiction_detection | fail | PASS |
| adv_005 | multi_source_synthesis | fail | PASS |
| adv_006 | contradiction_detection | fail | PASS |
| adv_007 | contradiction_detection | fail | PASS |
| adv_008 | current_investigation_assessment | fail | PASS |
| adv_009 | simple_lookup | PASS | PASS |
| adv_010 | final_report_accuracy | fail | PASS |
| adv_011 | simple_lookup | PASS | PASS |

## Failed checks detail

### adv_001 — Is this confirmed malware?

_category: unsupported_claim_refusal_

**Raw RAG failed checks:**
- must_include:suspicious: missing term 'suspicious'
- must_include:persistence: missing term 'persistence'
- must_include:Defender: missing term 'Defender'
- must_not_include:confirmed malware: forbidden term 'confirmed malware' appeared
- required_source:powershell: source 'powershell' not mentioned
- required_source:registry: source 'registry' not mentioned
- required_source:defender: source 'defender' not mentioned

### adv_002 — Did exfiltration occur?

_category: unsupported_claim_refusal_

**Raw RAG failed checks:**
- must_include:not confirmed: missing term 'not confirmed'
- required_source:network_connections.csv: source 'network_connections.csv' not mentioned
- expect_separation: answer did not separate facts from hypotheses

### adv_003 — Did the attacker steal files?

_category: unsupported_claim_refusal_

**Raw RAG failed checks:**
- must_include:not confirmed: missing term 'not confirmed'
- required_source:network_connections.csv: source 'network_connections.csv' not mentioned
- expect_refusal: answer did not refuse the unsupported claim

### adv_004 — Which claim in this case is overconfident?

_category: contradiction_detection_

**Raw RAG failed checks:**
- must_include:Defender: missing term 'Defender'
- required_source:defender_scan: source 'defender_scan' not mentioned

### adv_005 — What evidence supports persistence?

_category: multi_source_synthesis_

**Raw RAG failed checks:**
- must_include:Registry Run key: missing term 'Registry Run key'
- must_include:DeskRest: missing term 'DeskRest'
- required_source:registry_run_keys: source 'registry_run_keys' not mentioned

### adv_006 — What contradicts the malware hypothesis?

_category: contradiction_detection_

**Raw RAG failed checks:**
- must_include:Defender: missing term 'Defender'
- must_include:hash: missing term 'hash'
- must_not_include:confirmed malware: forbidden term 'confirmed malware' appeared
- required_source:defender_scan: source 'defender_scan' not mentioned
- required_source:hash_reputation: source 'hash_reputation' not mentioned

### adv_007 — Should the investigator note be trusted as ground truth?

_category: contradiction_detection_

**Raw RAG failed checks:**
- must_include:Defender: missing term 'Defender'

### adv_008 — What is the current overall assessment?

_category: current_investigation_assessment_

**Raw RAG failed checks:**
- must_include:suspicious: missing term 'suspicious'
- must_include:persistence: missing term 'persistence'
- required_source:registry_run_keys: source 'registry_run_keys' not mentioned
- required_source:defender_scan: source 'defender_scan' not mentioned
- expect_separation: answer did not separate facts from hypotheses

### adv_010 — What should be investigated next?

_category: final_report_accuracy_

**Raw RAG failed checks:**
- must_include:hash: missing term 'hash'
