# Obsidian Vault Template

This folder is a **template** for an Obsidian-friendly investigation
vault. It contains:

```
templates/
  case_index_template.md
  hypothesis_template.md
  ioc_template.md
  contradiction_template.md
  report_template.md
.obsidian/   (minimal default config so Obsidian opens cleanly)
```

You almost certainly do not need to edit the templates by hand. The
project's CLI fills them in:

```
python fw.py ingest raw_sources/<case>
python fw.py export-obsidian <case>
```

`export-obsidian` writes a ready-to-open vault under
`examples/obsidian_vault_<case_id>/`. Open *that* folder in Obsidian.

## When are these templates used?

- As a reference for what a "good" wiki page looks like.
- As a starting point when you want to seed a brand new case manually.
- As examples for the `schema/page_templates.md` rules. The AI follows
  those rules when it maintains the wiki.

## How to view a real vault in Obsidian

1. Run `python fw.py export-obsidian case_002_evolving`.
2. In Obsidian, **File → Open vault → Open folder as vault**.
3. Point Obsidian at `examples/obsidian_vault_case_002_evolving/`.
4. Toggle the **graph view** to see how `[[timeline]]`,
   `[[entities]]`, `[[hypotheses]]`, `[[contradictions]]`,
   `[[open_questions]]`, and `[[final_report]]` cross-link.
5. Use **backlinks** (right sidebar) to navigate evidence relationships.

## Do **not** edit these from Obsidian

- `raw_sources/` is **immutable**. The project's CLI / MCP server treat
  it as read-only ground truth.
- The `.fw/` sidecar (state, indexes, traces, graph, review queue) is
  internal. Don't try to maintain it by hand.

## How AI-proposed changes are reviewed

Risky wiki updates ("confirmed malware", "exfiltration occurred", etc.)
land in the review queue under `.fw/review_queue/` instead of being
applied directly. Use:

```
python fw.py review list <case>
python fw.py review show <case> <review_id>
python fw.py review approve <case> <review_id>
python fw.py review reject <case> <review_id>
```

See `docs/human_review.md`.
