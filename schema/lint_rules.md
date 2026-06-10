# Lint Rules

Lint inspects the compiled wiki and surfaces problems. Lint never modifies
files; it only reports. Findings are grouped by severity.

## High Severity

Findings that would mislead a reader or break the chain of evidence.

- **H1 Unsupported confirmation**: page asserts "confirmed malware",
  "confirmed exfiltration", "confirmed compromise", or similar without a
  matching `Confidence: High` or `Confidence: Confirmed` hypothesis backed by
  at least two independent supporting evidence bullets.
- **H2 Final report overclaim**: `final_report.md` contains language stronger
  than what `hypotheses.md` supports.
- **H3 Missing required page**: one of the required pages from
  `wiki_schema.md` is absent.
- **H4 Broken raw source citation**: a citation references a file under
  `raw_sources/` that does not exist.

## Medium Severity

Findings that weaken the wiki's quality but do not directly mislead.

- **M1 Hypothesis with no contradicting evidence section**: a hypothesis page
  has facts and inferences but no "Contradicting Evidence" subsection.
- **M2 Hypothesis with no supporting evidence**: a hypothesis lists an
  inference but cites no facts.
- **M3 Missing citation**: a Facts/Supporting/Contradicting bullet has no
  `Source:` or `Evidence:` marker.
- **M4 Stale page**: a page's `updated` front matter is older than the most
  recent ingest event.
- **M5 Broken wiki link**: an `[[other_page]]` link does not resolve to a
  real page or entity section.

## Low Severity

Hygiene findings.

- **L1 Duplicate entity**: two `entities.md` sections describe the same
  canonical entity.
- **L2 Orphan page**: a page exists that no other page links to.
- **L3 Orphan entity**: an entity is defined in `entities.md` but no other
  page references it.
- **L4 Empty section**: a templated section exists but has no content.
- **L5 Missing cross-reference**: an IOC row has no `Related` link.

## Example Output

```
HIGH:
- [H1] final_report.md says "malware confirmed" but the strongest
  hypothesis is Medium confidence (cases/case_001/final_report.md).

MEDIUM:
- [M1] hypotheses.md "Possible Registry-Based Persistence" has no
  Contradicting Evidence section.

LOW:
- [L3] entities.md defines `file: DeskRest.exe` but only `timeline.md`
  references it; consider linking from `iocs.md`.
```
