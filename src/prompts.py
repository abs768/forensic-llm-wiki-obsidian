"""Prompt fragments for the live LLM mode.

These are intentionally simple. The mock mode reproduces the same structure
deterministically, so live-mode prompts only need to describe the schema and
the maintenance principles, then let the model fill in the JSON.
"""
from __future__ import annotations

SYSTEM_PROMPT = """\
You are the maintainer of a Forensic LLM Wiki. You are given a raw forensic
evidence file and the current state of the case wiki. Your job is to extract
structured facts and propose updates.

Hard rules:
- Never invent facts that are not present in the raw source.
- Every fact must carry a citation back to either the raw source path or an
  existing wiki page.
- Distinguish facts, inferences, and hypotheses.
- Do not promote a hypothesis to a fact based on weak signals.
- Never use language like "confirmed malware" unless the evidence is
  overwhelming.
- Output strictly valid JSON conforming to the provided schema.
"""


def extraction_prompt(source_path: str, source_text: str, schema_hint: str) -> str:
    return f"""\
RAW SOURCE PATH: {source_path}

RAW SOURCE CONTENT:
---
{source_text}
---

Extract structured facts. Return JSON of the shape:

{schema_hint}

If a field has no entries, return an empty list. Do not include any text
outside the JSON object.
"""


SCHEMA_HINT = """\
{
  "source_path": "<path>",
  "entities": [{"type": "...", "value": "...", "appears_in": ["..."], "related": ["..."], "citations": [{"kind": "source", "target": "..."}]}],
  "events": [{"timestamp": "...", "description": "...", "citation": {"kind": "source", "target": "..."}}],
  "iocs": [{"artifact": "...", "type": "...", "first_seen": "...", "source": "...", "confidence": "Low|Medium|High|Confirmed", "reason": "...", "related": ["..."]}],
  "hypotheses": [{"title": "...", "confidence": "Low|Medium|High|Confirmed", "facts": ["..."], "inference": "...", "supporting_evidence": ["..."], "contradicting_evidence": ["..."], "open_questions": ["..."], "next_steps": ["..."]}],
  "contradictions": [{"title": "...", "claim_a": "...", "claim_b": "...", "status": "..."}],
  "open_questions": ["..."],
  "notes": ["..."]
}
"""
