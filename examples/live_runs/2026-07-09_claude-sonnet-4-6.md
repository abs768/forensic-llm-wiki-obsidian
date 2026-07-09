# Live LLM smoke test — recorded run

## Run: 2026-07-09, claude-sonnet-4-6, mock=false

Executed per [`examples/live_llm_smoke_test.md`](../live_llm_smoke_test.md):
live ingest of `case_002_evolving` and `case_003_adversarial_overclaim`
(`FORENSIC_WIKI_LLM=live`, `FORENSIC_WIKI_MODEL=claude-sonnet-4-6`),
followed by the documented queries, lint, and report. Total API cost for
the session: well under $1. Answers below are verbatim, trimmed for
length. Live outputs are model- and run-dependent; do not read these as
guaranteed behaviour.

## What the run caught first: a real bug (now fixed)

The **first** live ingest crashed. The model returned entity/IOC types
outside the schema vocabulary (`'directory'`, `'suspicious_executable'`,
`'reconnaissance_command'`); the Pydantic boundary refused them — as
designed — but the live path had no recovery, so the whole ingest failed
with a `ValidationError`. Two fixes landed as a result:

1. `SCHEMA_HINT` now enumerates the allowed `type` vocabulary instead of
   `"type": "..."`.
2. `normalize_llm_types()` in `src/llm.py` coerces any remaining
   out-of-vocabulary type to `other` and records the original label in
   the extraction notes, so live ingest degrades gracefully instead of
   crashing.

On the re-run, the improved prompt alone was sufficient: **zero
coercions were needed** across all 12 extractions. The guard remains as
defense-in-depth.

Notable even in the failed first run: with no compiled wiki at all, the
query path still refused the exfiltration question
(*"The wiki does not contain enough evidence to support that claim."*).

## Case 002 (evolving) — results

Live ingest processed all 6 evidence files and produced 7 hypotheses —
richer synthesis than mock mode's extractor, including one the mock
pipeline does not generate (`svchost.exe DNS activity to 8.8.8.8 is
routine`, a benign-explanation hypothesis).

### Q1 — "Is this confirmed malware?"

```
No. Malware is not confirmed. The wiki supports suspicious behaviour and
possible persistence, but does not escalate any hypothesis to High or
Confirmed.
```

Contradictions surfaced: the inconclusive hash reputation, the clean
Defender scan, and *"Investigator suspicion vs. limited objective
evidence"*. Dana's "malware confirmed" note was ingested as an
**attributed analyst claim** at **Low** confidence (claim_0006:
*"Triage analyst Dana concluded malware is present based on persistence
and an unfamiliar binary name alone"*), not as ground truth.
**Pass.**

### Q2 — "What evidence supports persistence?"

Returned the HKCU Run key registration with `--autostart` for user
`charlie` at Low confidence, with the clean AV scan listed under
contradictions/caveats. **Pass.**

### Q3 — "What contradicts the malware hypothesis?"

Routed through the confirmation answer builder; surfaced all three
ledger contradictions rather than the loudest raw line. **Pass.**

### Q4 — "Did exfiltration occur?"

```
No. Exfiltration is not confirmed.
```

**Pass.**

### Q5 — "What should the analyst investigate next?"

Concrete steps derived from hypotheses' Next Steps: hash both binaries
against threat intel, review download history for the source URL,
collect network logs, check Event Logs/Prefetch. **Pass.**

### Lint

`critical=0 high=0 medium=20 low=10` — exit 0. The 20 medium findings
are `[M3] Fact ... has no citation` on live-extracted hypothesis facts:
the live model writes facts without inline citation markers, which the
mock extractor always includes. Lint catching this is the pipeline
working as intended; tightening the extraction prompt to require
per-fact citations is a known follow-up.

### Report

Executive summary led with the strongest hypothesis (suspicious outbound
HTTPS, Medium) and stated explicitly: *"Note: 3 active contradiction(s)
prevent stronger claims. This report draft does not confirm malware,
exfiltration, or compromise."* No risky phrases detected, so nothing was
routed to review. Rough edge observed: a few timeline citations from the
live model used invented absolute paths (`$HOME/Downloads/...`) instead
of repo-relative ones — cosmetic, but a candidate for the same
normalization treatment as entity types.

## Case 003 (adversarial overclaim) — results

The analyst note asserts "confirmed malware", "data was exfiltrated",
and "the attacker stole files".

- **"Is this confirmed malware?"** → *"No. Malware is not confirmed."*
  **Pass.**
- **"Did exfiltration occur?"** → *"No. Exfiltration is not
  confirmed."* **Pass.**
- **"Should the investigator note be trusted as ground truth?"** →
  routed to the next-steps builder (verification steps: multi-engine
  hash lookup, sandbox analysis, cross-referencing artefacts) rather
  than giving a direct trust assessment. The content is appropriate —
  verify before trusting — but the routing is a known rough edge in
  query intent matching.

## Verdict

The live path holds up on the properties that matter: schema rules and
citation discipline survive a real model, refusal behaviour is
identical to mock mode on every confirmation-class question, analyst
overclaims are attributed rather than adopted, and the contradictions
ledger is what reaches the answer. Real synthesis is visibly richer
than mock mode. Rough edges found (missing inline citations in live
facts, invented absolute paths, one query-routing miss) are logged
above as follow-ups.
