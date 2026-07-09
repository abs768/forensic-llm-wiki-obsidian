"""LLM client.

Two modes:

- "mock" (default): the parsers + extractors produce the structured output
  directly. Deterministic, no network calls. Used by all tests and by the
  default CLI invocation.
- "live": calls the Anthropic API and asks Claude to extract the same
  structure. Used only when ``FORENSIC_WIKI_LLM=live`` is set.

The mock mode is not a stub. It runs the same parser / extractor pipeline
that live mode would post-process, so the wiki it produces is honest.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal, get_args

from . import claim_extractor, entity_extractor
from .parsers import parse
from .prompts import SCHEMA_HINT, SYSTEM_PROMPT, extraction_prompt
from .schemas import IOC, EntityType, ExtractedFacts, Hypothesis

Mode = Literal["mock", "live"]

_ALLOWED_ENTITY_TYPES = set(get_args(EntityType))


def normalize_llm_types(data: dict) -> dict:
    """Coerce out-of-vocabulary entity/IOC types from a live LLM to 'other'.

    Live models occasionally invent type labels outside the schema's
    vocabulary (e.g. 'directory', 'suspicious_executable'). Rather than
    failing the whole ingest, coerce them to 'other' and record the
    original label in the extraction notes so nothing is silently lost.
    Near-misses that only differ in case or spacing are mapped to the
    canonical spelling instead.
    """
    for key in ("entities", "iocs"):
        for item in data.get(key) or []:
            if not isinstance(item, dict):
                continue
            original = item.get("type", "")
            canonical = str(original).strip().lower().replace(" ", "_")
            if canonical in _ALLOWED_ENTITY_TYPES:
                item["type"] = canonical
            else:
                item["type"] = "other"
                data.setdefault("notes", []).append(
                    f"live extraction: unknown {key[:-1]} type "
                    f"{original!r} coerced to 'other'"
                )
    return data


class LLMClient:
    def __init__(self, mode: Mode | None = None) -> None:
        self.mode: Mode = mode or os.environ.get("FORENSIC_WIKI_LLM", "mock")  # type: ignore[assignment]
        if self.mode not in ("mock", "live"):
            raise ValueError(f"Unknown LLM mode: {self.mode}")

    def extract(
        self,
        path: Path,
        prior_hypotheses: list[Hypothesis],
        prior_iocs: list[IOC],
    ) -> ExtractedFacts:
        if self.mode == "live":
            return self._extract_live(path, prior_hypotheses, prior_iocs)
        return self._extract_mock(path, prior_hypotheses, prior_iocs)

    def _extract_mock(
        self,
        path: Path,
        prior_hypotheses: list[Hypothesis],
        prior_iocs: list[IOC],
    ) -> ExtractedFacts:
        source = parse(path)
        return ExtractedFacts(
            source_path=source.path,
            entities=entity_extractor.extract_entities(source),
            events=claim_extractor.extract_events(source),
            iocs=claim_extractor.extract_iocs(source),
            hypotheses=claim_extractor.extract_hypotheses(source),
            contradictions=claim_extractor.extract_contradictions(
                source, prior_hypotheses, prior_iocs,
            ),
            open_questions=claim_extractor.extract_open_questions(source),
        )

    def _extract_live(
        self,
        path: Path,
        prior_hypotheses: list[Hypothesis],
        prior_iocs: list[IOC],
    ) -> ExtractedFacts:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - depends on env
            raise RuntimeError(
                "Live mode requires the `anthropic` package. "
                "Install it or run with FORENSIC_WIKI_LLM=mock."
            ) from exc

        client = anthropic.Anthropic()
        text = path.read_text(encoding="utf-8", errors="replace")
        prompt = extraction_prompt(str(path), text, SCHEMA_HINT)
        message = client.messages.create(
            model=os.environ.get("FORENSIC_WIKI_MODEL", "claude-opus-4-7"),
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "".join(block.text for block in message.content if block.type == "text")
        # Strip optional code-fence wrapping.
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        data = json.loads(raw)
        # Always anchor the source path to what we read locally.
        data["source_path"] = str(path)
        facts = ExtractedFacts.model_validate(normalize_llm_types(data))

        # Live mode still benefits from the deterministic contradiction
        # detector — it knows the prior wiki state.
        source = parse(path)
        facts.contradictions.extend(
            claim_extractor.extract_contradictions(
                source, prior_hypotheses, prior_iocs,
            )
        )
        return facts
