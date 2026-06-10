# Benchmark Results — `case_002_evolving`

Two providers were scored against the same eval set:

1. **LLM Wiki** — the compiled wiki produced by `fw.py ingest`.
2. **Raw RAG** — naive BM25-style retrieval over `raw_sources/`.

## Scoring summary

| Metric | Raw RAG | LLM Wiki |
|---|---:|---:|
| Total questions | 16 | 16 |
| Passed | 4 | 16 |
| Failed | 12 | 0 |
| Unsupported claim failures | 0 | 0 |
| Missing source failures | 14 | 0 |
| Contradiction misses | 2 | 0 |
| Refusal accuracy | 0.33 | 1.00 |

## Per-question results

| ID | Category | Raw RAG | LLM Wiki |
|---|---|:---:|:---:|
| q01 | unsupported_claim_refusal | fail | PASS |
| q02 | unsupported_claim_refusal | fail | PASS |
| q03 | contradiction_detection | fail | PASS |
| q04 | contradiction_detection | fail | PASS |
| q05 | multi_source_synthesis | fail | PASS |
| q06 | multi_source_synthesis | fail | PASS |
| q07 | simple_lookup | fail | PASS |
| q08 | simple_lookup | PASS | PASS |
| q09 | simple_lookup | PASS | PASS |
| q10 | temporal_case_evolution | fail | PASS |
| q11 | temporal_case_evolution | PASS | PASS |
| q12 | final_report_accuracy | fail | PASS |
| q13 | final_report_accuracy | fail | PASS |
| q14 | unsupported_claim_refusal | fail | PASS |
| q15 | multi_source_synthesis | PASS | PASS |
| q16 | simple_lookup | fail | PASS |

## Failed checks detail

### q01 — Is this confirmed malware?

_category: unsupported_claim_refusal_

**Raw RAG failed checks:**
- must_include:suspicious: missing term 'suspicious'
- must_include:Defender: missing term 'Defender'
- required_source:powershell: source 'powershell' not mentioned
- required_source:registry: source 'registry' not mentioned
- required_source:defender: source 'defender' not mentioned

### q02 — Has data exfiltration been confirmed?

_category: unsupported_claim_refusal_

**Raw RAG failed checks:**
- must_include:outbound: missing term 'outbound'
- required_source:network_connections.csv: source 'network_connections.csv' not mentioned

### q03 — Does the investigator note conflict with other evidence?

_category: contradiction_detection_

**Raw RAG failed checks:**
- must_include:Defender: missing term 'Defender'
- required_source:defender_scan: source 'defender_scan' not mentioned

### q04 — What contradicts the suspicion that DeskRest.exe is malware?

_category: contradiction_detection_

**Raw RAG failed checks:**
- must_include:hash: missing term 'hash'
- required_source:hash_reputation: source 'hash_reputation' not mentioned

### q05 — What evidence supports persistence?

_category: multi_source_synthesis_

**Raw RAG failed checks:**
- must_include:Registry Run key: missing term 'Registry Run key'
- must_include:DeskRest: missing term 'DeskRest'
- required_source:registry_run_keys: source 'registry_run_keys' not mentioned

### q06 — Summarise the execution chain leading to DeskRest.exe.

_category: multi_source_synthesis_

**Raw RAG failed checks:**
- must_include:powershell: missing term 'powershell'
- must_include:DeskRest: missing term 'DeskRest'
- required_source:powershell_history: source 'powershell_history' not mentioned

### q07 — Are there any outbound network connections?

_category: simple_lookup_

**Raw RAG failed checks:**
- must_include:203.0.113.77: missing term '203.0.113.77'
- required_source:network_connections.csv: source 'network_connections.csv' not mentioned

### q10 — Was malware suspected before the hash reputation lookup completed?

_category: temporal_case_evolution_

**Raw RAG failed checks:**
- must_include:not confirmed: missing term 'not confirmed'
- expect_refusal: answer did not refuse the unsupported claim

### q12 — What is the overall current assessment of this case?

_category: final_report_accuracy_

**Raw RAG failed checks:**
- must_include:suspicious: missing term 'suspicious'
- must_include:persistence: missing term 'persistence'
- required_source:registry_run_keys: source 'registry_run_keys' not mentioned
- required_source:defender_scan: source 'defender_scan' not mentioned
- expect_refusal: answer did not refuse the unsupported claim

### q13 — Is the host compromised?

_category: final_report_accuracy_

**Raw RAG failed checks:**
- must_include:not confirmed: missing term 'not confirmed'
- must_include:suspicious: missing term 'suspicious'
- required_source:registry_run_keys: source 'registry_run_keys' not mentioned
- required_source:defender_scan: source 'defender_scan' not mentioned
- required_source:hash_reputation: source 'hash_reputation' not mentioned
- expect_refusal: answer did not refuse the unsupported claim

### q14 — Did DeskRest.exe definitely steal data?

_category: unsupported_claim_refusal_

**Raw RAG failed checks:**
- must_include:not confirmed: missing term 'not confirmed'
- expect_refusal: answer did not refuse the unsupported claim

### q16 — Is the DeskRest binary digitally signed?

_category: simple_lookup_

**Raw RAG failed checks:**
- must_include:not signed: missing term 'not signed'
