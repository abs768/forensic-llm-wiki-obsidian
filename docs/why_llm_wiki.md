# Why LLM Wiki?

A frequently asked question on this project is some variant of:

> *"Doesn't GraphRAG already establish relationships? Why do you need a
> wiki on top?"*

The short answer is at the bottom. The longer one starts here.

## What GraphRAG is good at

GraphRAG is a strong family of techniques for relationship-aware
retrieval. When the question is *"what is connected to what?"* — which
entities co-occur, which processes spawned which files, which IPs are
connected through which sessions — a graph index does the right thing.
You walk edges, ask one- or multi-hop relationship questions, and get
clean answers. This project ships a deliberately simple
**GraphRAG-lite** baseline (`src/graph/`) so the capability is visible
and benchmarked alongside the wiki.

This project does not claim GraphRAG is useless. It claims that
**relationships are not the whole problem** in a forensic investigation.

## What forensic investigations need that retrieval alone doesn't give

Working investigations need to maintain, over time:

- a **timeline** of events, ordered and citeable
- **entities** with cross-references and changing context
- **IOCs** with confidence and reason recorded
- **hypotheses** with separated facts / inferences / supporting evidence
  / contradicting evidence / open questions / next steps
- a **contradictions ledger** — explicit, named conflicts that must be
  reconciled before any conclusion can stand
- **open questions** the analyst is still chasing
- **confidence changes** as evidence arrives
- a **final report draft** that distinguishes facts from inferences from
  hypotheses
- an **analyst-readable knowledge base** so a teammate (or the same
  analyst tomorrow) can pick up the case without rebuilding context
  from raw evidence

None of those are retrieval problems. They are **state-maintenance
problems**. The wiki layer exists because the analyst needs more than a
fast index — they need a maintained notebook.

## The two layers, plainly

- The **wiki** acts like a maintained investigation notebook.
- The **graph** acts like a relationship index over the same evidence.

They complement each other. The included Hybrid mode literally glues
them together: start from the wiki's compiled assessment, append
graph-derived relationship context for entities mentioned in the
question.

## The core distinction

This is the line worth memorising:

> **GraphRAG answers:** *"What is connected to what?"*
> **LLM Wiki answers:** *"What do we currently believe, why, what
> contradicts it, and how did that belief change?"*

The first is a property of the corpus. The second is a property of the
investigation, and it cannot be reconstructed from retrieval alone.

## A concrete forensic example

From `case_002_evolving`, the question *"Is this confirmed malware?"*:

- **Raw RAG** quotes the analyst's *"possible malware infection"* note.
  It does not reconcile that against the Defender clean scan.
- **GraphRAG-lite** enumerates relationships around `DeskRest.exe`: it
  appears in `powershell_history.txt`, `registry_run_keys.reg`,
  `network_connections.csv`, `defender_scan.txt`, and
  `hash_reputation.txt`. Useful, but it cannot say what to believe.
- **LLM Wiki** answers *"No. Malware is not confirmed,"* lists the
  three open hypotheses with their `claim_NNNN` IDs and Medium / Low
  confidence, surfaces the Defender clean scan and the inconclusive
  hash reputation as contradicting evidence, and refuses to escalate.
- **Hybrid** prints the wiki's assessment first and then attaches the
  graph's relationship context as a footer. Best of both.

The included method benchmark scores these providers — plus an
embedding-based Vector RAG control — across 23 questions. On this synthetic case, the wiki and hybrid lead the
categories that require synthesis or refusal; the graph leads
relationship coverage cleanly. That is the intended outcome — see
`docs/threats_to_validity.md` for what these numbers do and do not
generalise to.

## Short answer

Forensic investigation needs **persistent state**, not just **better
retrieval**. The wiki maintains the state; the graph indexes the
relationships; the hybrid is best when you want both.
