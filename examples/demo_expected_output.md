# Demo expected output

Output below was captured from `bash examples/demo_commands.sh` in mock-LLM
mode. Timestamps will differ on your machine, but the structure and the
benchmark numbers should match exactly because the mock pipeline is
deterministic.

## Step 5 — malware question against compiled wiki

```
Answer:
No. Malware is not confirmed. The wiki supports suspicious behaviour and
possible persistence, but does not escalate any hypothesis to High or
Confirmed.

Assessment:
The wiki supports suspicious behaviour and possible persistence only.
The malware diagnosis remains an unsupported claim; no hypothesis is
rated High or Confirmed.

Evidence:
- claim_0001: Possible Outbound C2 Beacon — ...
- claim_0002: Possible Registry-Based Persistence — ...
- claim_0003: Suspicious Process Execution Chain — ...

Contradictions / caveats:
- Investigator suspicion vs. limited objective evidence: ...
- Suspicious activity vs. clean AV scan: Windows Defender full scan
  reported 0 threats (Source: raw_sources/case_001/defender_scan.txt).
- This should remain a medium-confidence hypothesis, not a confirmed conclusion.

Confidence:
Medium (hypothesis)
```

## Step 6 — wiki vs raw-source RAG, side by side

The naive RAG baseline retrieves and returns one snippet — the
investigator's "possible malware infection" note — without reconciling
it against the Defender clean scan:

```
[1] Forensic LLM Wiki — compiled answer
Answer:
No. Malware is not confirmed. ... [hypotheses, contradictions, sources]

[2] Naive raw-source RAG baseline
Answer:
Based on raw_sources/ keyword hits, the most relevant lines are shown
below. The baseline does not reconcile conflicting evidence.

- raw_sources/case_001/investigator_notes.md: Initial triage by analyst
  Bob suggests possible malware infection.
```

## Step 9 — case evolution

Each step ingests one drop of evidence and snapshots the wiki:

```
Evolved case 'case_002_evolving' across 6 step(s).
  step_01_powershell:        +1 files, 7 pages changed, eval 2/16
  step_02_registry:          +1 files, 7 pages changed, 1 new hyp, eval 2/16
  step_03_defender:          +1 files, 7 pages changed, 1 new contradiction, eval 5/16
  step_04_network:           +1 files, 7 pages changed, 1 new hyp, eval 8/16
  step_05_investigator_note: +1 files, 7 pages changed, 1 new contradiction, eval 11/16
  step_06_hash_reputation:   +1 files, 7 pages changed, 1 new contradiction, eval 16/16
```

The 2 → 2 → 5 → 8 → 11 → 16 climb is the compounding-knowledge claim made
visible: each evidence drop lets the wiki answer more questions correctly.

## Step 10 — snapshot diff between step 02 (registry) and step 03 (clean AV scan)

```
Diff: case_002_evolving/after_step_02_registry → case_002_evolving/after_step_03_defender

--- Page changed: index.md ---
@@ -10,7 +10,7 @@
 ## Current Assessment

-Strongest open hypothesis: Possible Registry-Based Persistence. (overall confidence: **Medium**)
+Strongest open hypothesis: Possible Registry-Based Persistence. 1 active contradiction(s) prevent firmer claims. (overall confidence: **Medium**)
```

The wiki softens its own assessment the moment the Defender clean scan
arrives. RAG cannot do this; it has nothing to soften.

## Step 11 — benchmark scorecard

```
| Metric                       | Raw RAG | LLM Wiki |
|------------------------------|--------:|---------:|
| Total questions              |      16 |       16 |
| Passed                       |       4 |       16 |
| Failed                       |      12 |        0 |
| Unsupported claim failures   |       0 |        0 |
| Missing source failures      |      14 |        0 |
| Contradiction misses         |       2 |        0 |
| Refusal accuracy             |    0.33 |     1.00 |
```

The 16 ÷ 4 ratio is the headline; the **1.00 vs 0.33 refusal accuracy** is
the more important one. The whole point of the wiki is that it refuses
the wrong answers RAG happily produces.
