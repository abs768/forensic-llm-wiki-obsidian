# Live demo script (≈ 5 minutes)

This script is for screen-recording or in-person walkthroughs. Each step
is a single command and a one-sentence explanation of what to point at.
The whole flow uses mock LLM mode — no API key needed.

## Setup (do this before recording)

```bash
git clone <repo> forensic-llm-wiki && cd forensic-llm-wiki
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"   # or:  pip install -r requirements.txt
```

Optional reset to guarantee a clean demo:

```bash
rm -rf wiki wiki_snapshots benchmark_results
```

## Talking script

### 1. "This is the raw evidence." — 10 s

```bash
ls raw_sources/case_001/
cat raw_sources/case_001/investigator_notes.md
```

> Six immutable evidence files: PowerShell history, registry, sysmon,
> network, an AV scan, and an analyst note that **says malware is
> confirmed**. Hold that thought.

### 2. "Watch the wiki compile from those files." — 30 s

```bash
python fw.py ingest raw_sources/case_001 --dry-run | head -20
python fw.py ingest raw_sources/case_001 --apply
ls wiki/cases/case_001/
```

> Dry-run shows the diffs we would write. Apply writes them. The wiki is
> just markdown — open it in any editor.

### 3. "Ask the wiki the malware question." — 30 s

```bash
python fw.py query case_001 "Is this confirmed malware?"
```

> The wiki says **no**, lists the supporting hypotheses with their
> `claim_NNNN` IDs, surfaces the contradicting Defender clean scan, and
> assigns Medium confidence. Note the citations to specific raw files.

### 4. "Now show what naive RAG does with the same question." — 30 s

```bash
python fw.py compare case_001 "Is this confirmed malware?" | tail -40
```

> The naive RAG baseline returns one snippet — the investigator's
> "possible malware infection" line. No contradictions, no synthesis.
> **This is the failure mode the wiki is designed to fix.**

### 5. "Lint catches overconfident claims." — 20 s

```bash
python fw.py lint case_001
```

> Four severity tiers; nothing critical or high on this case. If we
> hand-edited final_report.md to say "confirmed malware", lint would
> flag a Critical finding.

### 6. "Generate the draft report." — 15 s

```bash
python fw.py report case_001 | head -20
```

> The report keeps facts, inferences, and hypotheses separate and never
> elevates a Medium-confidence hypothesis into a confirmed conclusion.

### 7. "Now the killer demo: evidence arrives in waves." — 60 s

```bash
ls raw_sources/case_002_evolving/
python fw.py evolve case_002_evolving
```

> Six step directories. `evolve` ingests them one at a time and
> snapshots the wiki between steps. Watch the eval score climb
> monotonically: **2 → 2 → 5 → 8 → 11 → 16 of 16.**
> That climb *is* the compounding-knowledge claim, in numbers.

### 8. "Diff the wiki between two consecutive steps." — 30 s

```bash
python fw.py diff-snapshots case_002_evolving \
    after_step_02_registry after_step_03_defender | head -30
```

> The exact moment the wiki softens its assessment after the clean AV
> scan arrives. RAG cannot do this; it has nothing to soften.

### 9. "And the headline number." — 30 s

```bash
python fw.py benchmark case_002_evolving | head -22
```

> 16 questions, scored deterministically against both providers:
> **Wiki 16/16 vs RAG 4/16. Refusal accuracy 1.00 vs 0.33.**
> That's the case for compiled wikis in one line.

### 10. "Read the artifacts." — 30 s

```bash
cat benchmark_results/case_002_evolving/results.md | head -25
cat benchmark_results/case_002_evolving/evolution_report.md | head -40
ls examples/obsidian_vault_case_002/
```

> Everything we just did wrote auditable artifacts: the scorecard, the
> per-step narrative, and an Obsidian-compatible vault of the final
> wiki. Anyone can read these without re-running the code.

### Closing — 15 s

> The wiki is plain markdown. The schema rules are plain markdown.
> The benchmark scorecard is plain markdown. There is no database,
> no vector index, no frontend, no LLM-as-judge. The mechanism that
> makes this work — and the mechanism that makes it auditable — is
> the same.

## Optional: pytest before recording

```bash
pytest          # 90+ tests, mock mode, no API keys
ruff check .
```
