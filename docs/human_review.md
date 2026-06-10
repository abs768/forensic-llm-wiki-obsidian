# Human review for risky conclusions

The wiki is maintained by an LLM. The lint rules catch many mistakes,
but some conclusions are too consequential to apply blindly — the
classic case is the AI proposing **"confirmed malware"** based on
incomplete evidence. The review queue exists to hold those updates back
until a human approves.

## What counts as "risky"

The same phrase list lint cares about:

- `confirmed malware` / `malware confirmed`
- `confirmed exfiltration` / `exfiltration occurred` / `data was stolen`
- `confirmed compromise`
- `definitely malicious` / `definite malware`

A line **only** counts as risky when it is *asserting* the phrase. Lines
that *quote* the phrase ("Investigator note: Dana asserts: malware
confirmed") are excluded — the wiki is allowed to record an overclaim
faithfully without itself making it.

## How review is triggered

### `ingest --review`

```bash
python fw.py ingest raw_sources/case_002_evolving --review
```

If a freshly-rendered page contains a risky phrase that the prior page
did not, the page is **reverted on disk** and the proposed content is
queued as a `ReviewItem` under `.fw/review_queue/`. Safe pages still
update normally. The wiki's structured state and indexes still reflect
extraction; only the markdown rendering of risky pages is held.

### `report --review`

```bash
python fw.py report case_002_evolving --review
```

If the proposed `final_report.md` contains a risky phrase, the existing
report is preserved and the proposed body is queued.

### Via MCP

The `ingest_case_sources` and `generate_report` MCP tools accept a
`review: true` flag with the same semantics.

## Reviewing items

```bash
python fw.py review list case_002_evolving
python fw.py review list case_002_evolving --status pending
python fw.py review show case_002_evolving review_0001
python fw.py review approve case_002_evolving review_0001 --reason "Backed by ..."
python fw.py review reject  case_002_evolving review_0001 --reason "Not yet supported"
```

- **list** shows ID, status, target page, and the detected risky
  phrase(s).
- **show** prints the full proposed content alongside the audit
  metadata.
- **approve** writes the proposed content to the target page and
  records the decision.
- **reject** leaves the wiki unchanged and records the decision.

Every action is appended to `.fw/review_history.jsonl` so the chain of
custody for the wiki is auditable.

## What review does **not** do

- It does not block the structured `state.json` from being updated.
  Indexes always reflect what extraction found; this is intentional so
  query / lint can reason about the proposed content.
- It does not retroactively undo prior writes. If a risky claim made
  it into the wiki before review existed, run `git diff` against an
  earlier snapshot and reconcile manually.
- It is not an authentication system. There is no notion of "who"
  approved — a single trusted operator is assumed. For a multi-reviewer
  workflow, wrap the CLI in your own approval system.

## Why this design

The LLM Wiki architecture treats the markdown wiki as the analyst's
working memory. A single confident-but-wrong sentence in
`final_report.md` is the kind of mistake that gets quoted downstream.
The review queue is a small, file-based brake: cheap to operate, easy
to audit, and impossible to confuse with the immutable raw evidence.
