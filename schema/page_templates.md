# Page Templates

Use these templates as the canonical structure for each wiki page. Sections
may grow, but the headings and section order must remain stable so lint and
diff stay readable.

## index.md

```md
---
case: <case_id>
page: index
updated: <ISO timestamp>
sources: <count>
---

# Case <case_id>

## Current Assessment

<one-paragraph summary, with confidence>

## Key Evidence

- bullet list of major artifacts with citations

## Key Open Questions

- bullets, link to [[open_questions]]

## Pages

- [[timeline]]
- [[entities]]
- [[iocs]]
- [[hypotheses]]
- [[contradictions]]
- [[open_questions]]
- [[final_report]]
```

## timeline.md

```md
# Timeline

| Timestamp           | Event                       | Source                       |
|---------------------|-----------------------------|------------------------------|
| 2025-11-12 10:14:02 | powershell.exe spawned ...  | raw_sources/.../sysmon...csv |
| unknown             | Registry Run key created    | raw_sources/.../registry...  |
```

Mark uncertain timestamps as `unknown` or `~approx`.

## entities.md

```md
# Entities

## process: powershell.exe
- Type: process
- Value: powershell.exe
- Appears in: [[timeline]], raw_sources/.../sysmon_processes.csv
- Related: [[entities#file: DeskRest.exe]]
- Citations:
  - raw_sources/case_001/sysmon_processes.csv

## file: DeskRest.exe
- Type: file
- ...
```

## iocs.md

```md
# Indicators of Compromise

| Artifact       | Type     | First Seen          | Source                           | Confidence | Reason                                                | Related            |
|----------------|----------|---------------------|----------------------------------|------------|-------------------------------------------------------|--------------------|
| DeskRest.exe   | file     | 2025-11-12 10:14:02 | raw_sources/.../sysmon...csv     | Medium     | Launched by powershell, persistence Run key present   | [[hypotheses]]     |
```

## hypotheses.md

Every hypothesis must use this template exactly:

```md
## <Hypothesis Title>

Confidence: <Low|Medium|High>

### Facts
- bullets, each with citation

### Inference
- short paragraph

### Supporting Evidence
- bullets, each with citation

### Contradicting Evidence
- bullets, each with citation. If none known, write
  "None recorded — see [[contradictions]] for active conflicts."

### Open Questions
- bullets

### Next Steps
- bullets
```

## contradictions.md

```md
# Contradictions

## Suspicious executable vs. clean AV scan

- Claim A: DeskRest.exe is suspicious (source: [[hypotheses]])
- Claim B: Defender scan reports no threat (source: raw_sources/.../defender_scan.txt)
- Status: Unresolved. AV may be unaware of the binary, or behavior is benign.
```

## open_questions.md

```md
# Open Questions

- [ ] Is DeskRest.exe digitally signed?
- [ ] What is the SHA-256 hash reputation of DeskRest.exe?
```

## final_report.md

```md
# Final Report — Case <case_id>

> Draft. Distinguishes facts, inferences, and hypotheses. Do not promote
> hypotheses to facts without strong evidence.

## Executive Summary
## Timeline
## Key Artifacts
## Indicators of Compromise
## Hypotheses
## Contradictions
## Recommended Next Steps
## Appendix: Sources
```
