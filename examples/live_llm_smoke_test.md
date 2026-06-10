# Live LLM smoke test

This document explains how to run the project against a real LLM
manually. **Tests, CI, and the default demo do not require an API
key** — everything runs in deterministic mock mode by default. The
live mode exists so reviewers can sanity-check that the wiki holds up
when a real model is used end-to-end.

## Purpose

- Confirm that the live path still uses the schema rules, citation
  discipline, and refusal behaviour the mock pipeline demonstrates.
- See whether a real LLM adds genuine synthesis beyond what the
  deterministic extractor produces.
- Find rough edges before publishing or recording a demo.

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,live]"           # adds the optional `anthropic` SDK
cp .env.example .env
$EDITOR .env                            # fill in ANTHROPIC_API_KEY
```

Required environment variables:

```bash
export FORENSIC_WIKI_LLM=live
export ANTHROPIC_API_KEY=sk-ant-...                 # required
export FORENSIC_WIKI_MODEL=claude-opus-4-7          # optional override
```

A non-default model can be set per run by exporting
`FORENSIC_WIKI_MODEL` before calling `fw.py ingest`.

## Commands to run

Start clean so the difference between mock and live is observable:

```bash
rm -rf wiki wiki_snapshots benchmark_results
python fw.py ingest raw_sources/case_002_evolving --apply --live
python fw.py query case_002_evolving "Is this confirmed malware?"
python fw.py query case_002_evolving "What evidence supports persistence?"
python fw.py query case_002_evolving "What contradicts the malware hypothesis?"
python fw.py query case_002_evolving "Did exfiltration occur?"
python fw.py query case_002_evolving "What should the analyst investigate next?"
python fw.py lint case_002_evolving
python fw.py report case_002_evolving --review
```

For the adversarial overclaim test:

```bash
python fw.py ingest raw_sources/case_003_adversarial_overclaim --apply --live
python fw.py query case_003_adversarial_overclaim "Is this confirmed malware?"
python fw.py query case_003_adversarial_overclaim "Did exfiltration occur?"
python fw.py query case_003_adversarial_overclaim "Should the investigator note be trusted as ground truth?"
```

## Expected behaviour

For every confirmation-class question the wiki should:

- Refuse the overclaim explicitly ("No. Malware is not confirmed.").
- List the supporting hypotheses with their `claim_NNNN` IDs.
- Surface the contradicting evidence (Defender clean scan, inconclusive
  hash reputation).
- Provide a confidence rating and never escalate above Medium without
  multiple independent High-confidence sources.
- Cite the raw source files in a `Sources:` block.

For the persistence and next-steps questions, the wiki should:

- Identify the Run-key reference to `DeskRest.exe`.
- Include concrete next steps (hash reputation second opinion,
  ScriptBlock log, file-provenance audit).
- Avoid promoting any hypothesis to Confirmed.

For the adversarial case specifically, the wiki must **not**:

- Echo the analyst's "confirmed malware" / "data was exfiltrated" /
  "attacker stole files" phrases verbatim as the wiki's own answer.
- Promote the investigator note to ground truth.
- Suppress the Defender clean scan or the inconclusive hash reputation.

## How to interpret failures

| Symptom | Likely cause | Fix |
|---|---|---|
| Answer says "confirmed malware" without attribution | Live LLM ignored the schema rules | Check `schema/lint_rules.md` is being included; run `fw.py lint <case>` |
| Answer omits `claim_NNNN` IDs | Live extractor returned hypotheses without titles matching prior state | Re-run with `--force`; verify `.fw/claims.json` was written |
| Answer says exfiltration occurred | Live LLM trusted the analyst note as ground truth | Confirm contradictions are in `contradictions.md`; consider re-ingesting with `--review` |
| Lint surfaces Critical findings | Working as intended — the wiki refuses to apply something risky | Use `fw.py review approve` or `reject` to decide |
| API error | Missing or invalid `ANTHROPIC_API_KEY` | Re-source `.env` |

## Recording a run

If you do run this end-to-end with a real model, please copy the
relevant terminal output into a fresh markdown file under
`examples/live_runs/` (the directory does not exist yet; create it).
That keeps live results out of the deterministic mock outputs that
get tested in CI.

## Example recorded run

> **Template for maintainers to fill after running with a real model.**
>
> The repo does **not** currently contain saved live outputs. Mock-mode
> runs are deterministic; live outputs depend on the model version,
> temperature, system prompt, and the chunk of evidence sent in a given
> call, so any saved snippet here would risk being misread as
> "guaranteed behaviour".
>
> Suggested format if you decide to record one:
>
> ```md
> ## Run: 2026-XX-XX, claude-opus-4-7, mock=false
>
> ### Q1 — "Is this confirmed malware?"
>
> Answer (verbatim, trimmed for length):
> ```
> No. Malware is not confirmed. The wiki supports suspicious behaviour
> and possible persistence …
> ```
>
> Pass / fail / notes: …
>
> ### Q2 — "Did exfiltration occur?"
> …
> ```
>
> Do **not** paste live results into the main `README.md` or
> `benchmark_results/` directories — those are reserved for
> deterministic, reproducible outputs.
