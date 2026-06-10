# Obsidian Vault — `case_002_evolving`

This folder is a snapshot of the **final** compiled wiki for the
evolving demo case (`case_002_evolving`), captured after all six evidence
drops have been ingested.

It is included for two reasons:

1. To let anyone browse the wiki without running the project.
2. To demonstrate that the wiki is just **markdown files with wiki links** —
   open this folder in [Obsidian](https://obsidian.md/) and the graph view
   will render `[[timeline]]`, `[[entities]]`, `[[iocs]]`, `[[hypotheses]]`,
   `[[contradictions]]`, `[[open_questions]]`, and `[[final_report]]` as a
   linked knowledge base.

## How to view in Obsidian

1. Install Obsidian.
2. Choose "Open folder as vault" and point at this directory.
3. The graph view shows every page and how they cross-reference.
4. Each `claim_NNNN`, `evt_NNNN`, and `ent_NNNN` ID in the markdown is the
   stable identifier of a structured entry in the corresponding
   `.fw/{claims,events,entities}.json` index from the live wiki.

## Regenerating this vault

```bash
python fw.py evolve case_002_evolving
cp wiki_snapshots/case_002_evolving/after_step_06_hash_reputation/*.md \
   examples/obsidian_vault_case_002/
```

Obsidian is **not** a runtime dependency of the project — this is a
demo-friendly artifact, nothing else.

## What you should notice

- `index.md` carries the **current assessment** with a confidence rating.
- `hypotheses.md` separates **facts** from **inferences** for every
  hypothesis, and every hypothesis carries a `claim_NNNN` ID.
- `contradictions.md` records both the **investigator-vs-evidence** and
  the **persistence-vs-clean-AV** contradictions explicitly.
- `final_report.md` keeps facts and hypotheses separate; it does **not**
  confirm malware despite the investigator note's "malware confirmed"
  overclaim.
- No page asserts a conclusion the underlying evidence cannot back.
