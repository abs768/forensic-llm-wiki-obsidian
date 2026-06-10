# Citation Rules

A fact without a citation is not a fact. Every factual claim in the wiki must
cite either a raw source file or another wiki page.

## Format

Cite a raw source as:

```
Source: raw_sources/<case>/<file>
```

Cite another wiki page as:

```
Evidence: [[<page>]] → <short description>
```

Both forms may appear together when a wiki page summarises a raw source.

## Required Citations

The following claim types must always carry a citation:

- Any timeline entry
- Any entity attribute (where it appeared, related entities)
- Any IOC row
- Any "Facts" bullet under a hypothesis
- Any "Supporting Evidence" or "Contradicting Evidence" bullet
- Any factual claim in `final_report.md`

## Optional Citations

The following are LLM-derived and need not cite, but should be clearly marked
as inference, not fact:

- "Inference" sections of hypotheses
- "Current Assessment" prose on `index.md` (which must still link back to
  hypotheses and contradictions)

## Forbidden

- Citing a wiki page as evidence for itself
- Citing a raw source that does not exist (lint will flag)
- Reusing the citation of an unrelated fact ("citation laundering")
