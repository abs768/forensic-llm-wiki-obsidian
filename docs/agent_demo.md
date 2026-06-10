# Agent demo

These traces show an MCP-connected agent using the project as a
maintained investigation wiki — not as raw document search.

The point: the agent reads the **compiled wiki state**, surfaces
contradictions, and refuses unsupported claims. The wiki is the
agent's working memory.

## Example 1 — *"Is this confirmed malware?"*

**User**

> Inspect `case_002_evolving`. Is this confirmed malware?

**Agent tool calls**

1. `list_cases` → confirms `case_002_evolving` exists, has both
   `raw_sources/` and `wiki/`.
2. `get_case_summary(case_id="case_002_evolving")` → reads `index.md`,
   sees Medium confidence on persistence.
3. `read_wiki_page(case_id="case_002_evolving", page="hypotheses.md")`
   → enumerates the three open hypotheses with `claim_NNNN` IDs and
   their facts/inferences.
4. `get_contradictions(case_id="case_002_evolving")` → AV-clean vs
   suspicious activity, investigator overclaim vs limited objective
   evidence, malware suspicion vs inconclusive hash reputation.
5. `query_case(case_id="case_002_evolving", question="Is this confirmed malware?")`
   → wiki's compiled refusal answer with citations.
6. `lint_case(case_id="case_002_evolving")` → no Critical / High
   findings; the wiki is internally consistent.

**Expected agent answer**

> No. The current wiki supports suspicious execution and possible
> persistence, but not confirmed malware. The Defender scan reports zero
> threats and the hash reputation lookup returned an inconclusive
> verdict, so a confirmed-malware conclusion would override existing
> contradicting evidence. The wiki's strongest hypothesis is
> `claim_0002 Possible Registry-Based Persistence` at Medium
> confidence. To escalate further, the analyst should obtain a hash
> reputation result and a second-opinion AV scan — both are tracked as
> open questions.

The agent's answer is the wiki's compiled assessment, not a retrieval
of the analyst's "possible malware infection" note.

## Example 2 — *"What should I investigate next?"*

**User**

> What should I investigate next?

**Agent tool calls**

1. `get_open_questions(case_id="case_002_evolving")` → loads
   `open_questions.md` and parses each bullet.
2. `read_wiki_page(case_id="case_002_evolving", page="hypotheses.md")`
   → cross-references each hypothesis's "Next Steps" section.
3. `lint_case(case_id="case_002_evolving")` → checks whether any
   safety rules are firing (e.g., a contradiction in state but not in
   the rendered page).
4. `query_case(case_id="case_002_evolving",
   question="What next steps are supported by the evidence?")` → wiki
   answer with the prioritised next-step list.

**Expected agent answer**

> Three concrete next steps are recorded in the wiki:
>
> 1. Hash and reputation-check the binary against a second feed — open
>    question on `claim_0002`.
> 2. Pull the PowerShell ScriptBlock log for the parent session, since
>    the execution chain is interactive — open question on `claim_0003`.
> 3. Confirm whether the autostart entry was created by a legitimate
>    installer or by post-exploit activity — open question on
>    `claim_0002`.
>
> All three are derivable from the current wiki; none of them require
> re-reading raw sources. Once any of these complete, run
> `fw.py ingest raw_sources/case_002_evolving` (or
> `ingest_case_sources` via MCP) and re-run `query_case` to see how the
> Medium-confidence hypothesis moves.

## Why this matters

A retrieval-only setup would have to re-search the corpus for each
question and reconstruct the analyst's reasoning from raw lines. Here
the agent reads the wiki, which already contains the synthesis. That
is the LLM Wiki architecture's selling point made concrete.
