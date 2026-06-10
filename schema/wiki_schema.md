# Wiki Schema

This document defines the structure of every case wiki. The LLM that maintains
the wiki must obey this schema when ingesting evidence or producing new pages.

## Three-Layer Model

| Layer | Path                  | Mutability                          | Owner            |
|-------|-----------------------|-------------------------------------|------------------|
| 1     | `raw_sources/`        | Immutable, never written by the LLM | Investigators    |
| 2     | `wiki/`               | LLM-owned, compiled knowledge       | LLM (maintainer) |
| 3     | `schema/`             | Human + LLM co-evolved              | Project          |

The wiki is the only layer the LLM mutates. Raw sources are the ground truth
and must be cited.

## Case Folder Layout

Every case lives under `wiki/cases/<case_id>/` and must contain the following
pages. A missing page is itself a lint finding.

```
wiki/cases/<case_id>/
  index.md              # case summary, current assessment, links
  timeline.md           # chronological events
  entities.md           # processes, files, users, hosts, IPs, hashes, etc.
  iocs.md               # indicators of compromise
  hypotheses.md         # investigation hypotheses, separated facts vs inferences
  contradictions.md     # evidence conflicts
  open_questions.md     # what still needs investigation
  final_report.md       # report draft, facts vs hypotheses kept separate
```

## Page Contract

Each page must include:

1. A YAML-style front matter with `case`, `page`, `updated`, `sources`.
2. A short purpose statement.
3. Structured sections defined in `page_templates.md`.
4. Citations on every factual claim (see `citation_rules.md`).

## Cross-Linking

- Pages refer to each other via Obsidian-style wiki links: `[[timeline]]`,
  `[[entities#DeskRest.exe]]`.
- Every entity introduced in `entities.md` should be referenced from at least
  one other page or flagged as orphan by lint.
- Hypotheses must link to supporting and contradicting evidence pages.

## Confidence Levels

Hypotheses and assessments must declare a confidence:

- `Low`     — single weak signal, easily explained otherwise
- `Medium`  — multiple corroborating signals but alternative explanations
              remain
- `High`    — strong, independent, hard-to-deny evidence
- `Confirmed` — reserved for facts directly observed in raw sources
