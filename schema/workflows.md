# Workflows

The forensic wiki has exactly three first-class workflows. Each follows the
same safe pattern: read, propose structured updates, validate, apply, lint.

## 1. Ingest

Triggered by `fw.py ingest raw_sources/<case>`.

Steps:

1. Enumerate every file in the case raw folder.
2. For each file:
   a. Detect file type using `parsers.py`.
   b. Extract structured facts: entities, events, IOCs, observations.
   c. Pair every fact with its source citation.
3. Merge new facts into the current wiki:
   - Add new entities to `entities.md`, deduplicating by canonical value.
   - Append events to `timeline.md` in chronological order.
   - Update or create IOC rows in `iocs.md`.
   - Update affected hypotheses; create new ones only if evidence warrants.
   - Append contradictions when new facts conflict with prior wiki claims.
   - Refresh `index.md` summary and `open_questions.md`.
4. Validate proposed updates against `wiki_schema.md` and `citation_rules.md`.
5. Apply updates to markdown files atomically.
6. Run lint and surface findings.

Ingest must update multiple pages at once. A registry artifact, for example,
will touch `timeline.md`, `entities.md`, `iocs.md`, `hypotheses.md`, and
possibly `contradictions.md`.

## 2. Query

Triggered by `fw.py query <case> "<question>"`.

Steps:

1. Read the compiled wiki for the case.
2. Answer using wiki content first.
3. Fall back to raw sources only if the wiki is incomplete on that topic.
4. Compose a structured answer with:
   - direct answer
   - supporting wiki pages
   - supporting raw source citations
   - confidence
   - contradictions / caveats
   - classification: fact / inference / hypothesis
5. If the wiki cannot support an answer, return the literal string
   `The wiki does not contain enough evidence to support that claim.`
   Do not hallucinate.

## 3. Lint

Triggered by `fw.py lint <case>`.

Steps:

1. Load all wiki pages for the case.
2. Apply every rule in `lint_rules.md`.
3. Group findings by severity (High / Medium / Low).
4. Print a report. Lint never modifies the wiki.

## Optional: Report

Triggered by `fw.py report <case>`. Produces `final_report.md` by composing
the existing wiki pages. Must preserve the fact/inference/hypothesis
distinction defined in `page_templates.md`.
