# Obsidian workflow

The compiled wiki is plain markdown with `[[wiki links]]`, which makes
it an Obsidian vault. Opening it in Obsidian gives you:

- A graph view of how `[[timeline]]`, `[[entities]]`, `[[iocs]]`,
  `[[hypotheses]]`, `[[contradictions]]`, `[[open_questions]]`, and
  `[[final_report]]` reference each other.
- Backlinks in the right sidebar — click any entity or claim ID and
  see every page that mentions it.
- Native rendering of Mermaid diagrams, so the GraphRAG-lite
  `graph.mmd` is browsable as a diagram.

## Export a vault

```bash
python fw.py export-obsidian case_002_evolving
```

This writes a clean export to
`examples/obsidian_vault_case_002_evolving/` containing:

```
index.md
timeline.md
entities.md
iocs.md
hypotheses.md
contradictions.md
open_questions.md
final_report.md
graph.mmd                 (if graph-build has run)
README_FOR_OBSIDIAN.md    (orientation)
```

The internal `.fw/` sidecar is **not** exported. The vault is for
humans, not for round-tripping internal state.

## Open the vault

1. Launch Obsidian.
2. File → **Open vault** → **Open folder as vault**.
3. Point Obsidian at the exported folder.

## Recommended pages to inspect

- `index.md` — current assessment, top open questions, links to every
  other page.
- `hypotheses.md` — facts / inference / supporting / contradicting per
  hypothesis, with `claim_NNNN` IDs.
- `contradictions.md` — the explicit conflicts the wiki has reconciled.
- `final_report.md` — the report draft, with facts and hypotheses
  cleanly separated.
- `graph.mmd` — relationship overview (open as Mermaid).

## How backlinks help

Right-click any entity (e.g. `DeskRest.exe`) in `entities.md` and
choose **Show backlinks**. You'll see every page that mentions it —
the timeline event, the IOC row, the persistence hypothesis. That's
the same picture the GraphRAG-lite graph encodes, surfaced through
plain markdown wiki-links.

## What not to edit manually

- `raw_sources/` is immutable ground truth. Do **not** edit raw
  evidence in Obsidian.
- The exported vault is a **snapshot**, not the live wiki. Edits in
  Obsidian will be overwritten on the next
  `python fw.py export-obsidian <case>`.
- Don't manually rewrite `final_report.md` from Obsidian without
  also running `python fw.py lint <case>` afterwards — the safety
  rules will catch unsupported claims.

## Snapshots and time travel

`fw.py evolve <case>` writes snapshots after each evidence drop into
`wiki_snapshots/<case>/`. To browse any snapshot in Obsidian, copy
the snapshot folder somewhere and open it as a vault — or run
`fw.py diff-snapshots <case> after_step_02 after_step_03` to see the
markdown changes in unified-diff form.

## How AI-proposed changes get reviewed

The CLI's `--review` mode (and the matching MCP tool) holds any wiki
update that contains a risky phrase ("confirmed malware",
"exfiltration occurred", …) in `.fw/review_queue/`. See
`docs/human_review.md` for the approve/reject flow.

When you re-export after approving a review item, the vault picks up
the change. The investigator sees the new content; the audit log
records who approved and when.
