# Demo video script (2 – 3 minutes)

A crisp, recordable walkthrough. Each step lists the exact command,
what the viewer should see, and the voiceover line.

Recommended terminal: any shell at 80 cols or wider. Run `make clean`
before recording so the demo starts from a known empty state.

## Setup (do once)

```bash
git clone <repo> && cd forensic-llm-wiki
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
make clean
```

## 1. README hook + thesis (15 s)

**On screen:** open `README.md` in the editor; scroll to the
one-sentence hook and the four-line thesis.

> *"Forensic LLM Wiki is a markdown-first AI investigation system
> that compiles raw forensic evidence into an evolving
> Obsidian-compatible case wiki instead of answering from raw snippets
> every time like traditional RAG."*
>
> *"RAG retrieves. GraphRAG relates. LLM Wiki maintains evolving case
> state. Hybrid combines them."*

## 2. The evidence (10 s)

```bash
ls raw_sources/case_002_evolving/
cat raw_sources/case_002_evolving/step_05_investigator_note/investigator_notes.md
```

> *"Six evidence drops arrive in sequence. Step 5 is the analyst
> note. Hold that thought."*

## 3. Evolve through every step (35 s)

```bash
python fw.py evolve case_002_evolving
```

**On screen:** the per-step summary table.

> *"Each step ingests one drop, snapshots the wiki, runs lint and
> eval. Watch the eval score climb: 2, then 2, then 5, 8, 11, and 16
> of 16. The eval climbs monotonically as evidence accumulates."*

## 4. Hypothesis history + snapshot diff (20 s)

```bash
cat wiki/cases/case_002_evolving/.fw/hypothesis_history.json | head -25
python fw.py diff-snapshots case_002_evolving \
    after_step_02_registry after_step_03_defender | head -30
```

> *"Every step writes a snapshot. Hypothesis history tracks per-step
> confidence. The diff between step 02 and step 03 shows the moment
> the wiki softens its assessment after the Defender clean scan
> arrives."*

## 5. Open the Obsidian vault (20 s)

```bash
python fw.py export-obsidian case_002_evolving
```

**On screen:** open `examples/obsidian_vault_case_002_evolving/` in
Obsidian. Switch to graph view.

> *"The wiki is plain markdown. Open it in Obsidian for the graph
> view — timeline, entities, hypotheses, contradictions all linked.
> The internal sidecar is intentionally not exported."*

## 6. Hypotheses and contradictions (15 s)

In Obsidian, open `hypotheses.md`, then `contradictions.md`.

> *"Every hypothesis carries a `claim_NNNN` ID and separates facts
> from inferences from supporting and contradicting evidence.
> Contradictions are first-class — that's why the wiki refuses
> overclaims."*

## 7. Four-way comparison (20 s)

```bash
python fw.py compare-all case_002_evolving "Is this confirmed malware?"
```

**On screen:** all four answers in sequence.

> *"Raw RAG retrieves the analyst's possible-malware-infection line.
> GraphRAG-lite enumerates relationships. LLM Wiki refuses with
> citations and the contradicting Defender scan. Hybrid combines the
> wiki's assessment with the graph's relationship context."*

## 8. The benchmark scorecard (20 s)

```bash
python fw.py benchmark-methods case_002_evolving | head -22
```

**On screen:** the scoring table.

> *"Same 23 questions, four providers, deterministic scoring. Hybrid
> 20 / 23. LLM Wiki 19 / 23. Raw RAG 7 / 23. GraphRAG-lite 5 / 23.
> Wiki and Hybrid lead refusal and contradiction; graph leads
> relationship coverage."*

## 9. Adversarial overclaim case (20 s)

```bash
python fw.py ingest raw_sources/case_003_adversarial_overclaim --apply
python fw.py query case_003_adversarial_overclaim "Did exfiltration occur?"
python fw.py benchmark case_003_adversarial_overclaim | head -18
```

> *"Adversarial test. The analyst note explicitly says 'data was
> exfiltrated' and 'the attacker stole files'. The wiki refuses both,
> surfaces the Defender clean scan and inconclusive hash reputation
> as contradicting, and passes 11 of 11 while raw RAG passes 2 of
> 11."*

## 10. Review queue catches risky updates (15 s)

```bash
python fw.py report case_003_adversarial_overclaim --review
python fw.py review list case_003_adversarial_overclaim
```

> *"Risky updates land in `.fw/review_queue/` instead of being applied
> blindly. A human approves or rejects. The decision lands in
> `review_history.jsonl` for an auditable chain of custody."*

## 11. Close (10 s)

**On screen:** back to the editor, thesis line highlighted.

> *"RAG retrieves. GraphRAG relates. LLM Wiki maintains evolving
> case state. Hybrid combines them. Plain markdown, no database, no
> vector store, 196 tests passing without an API key. Repo link in
> the description."*

## Recording tips

- Terminal font at least 16 pt.
- Use `make clean` between rehearsal takes.
- Record at 1080p; the markdown tables read poorly below that.
- Target length **2:30 – 3:00**. Step 3 (`evolve`) is the natural
  pacing target; everything else trims to fit.
