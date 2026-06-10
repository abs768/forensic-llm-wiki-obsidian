"""Structured JSON indexes derived from ``WikiState``.

We write three sidecar files alongside the markdown wiki:

  .fw/events.json    — every Event, with a stable evt_NNNN id
  .fw/entities.json  — every Entity, with a stable ent_NNNN id
  .fw/claims.json    — every Hypothesis (and IOC) as a structured claim

The markdown wiki remains the user-facing layer. These JSON files exist so
``query``, ``lint``, ``eval``, and downstream tooling can reason over the
same evidence without re-parsing markdown.
"""
from __future__ import annotations

import json
from pathlib import Path

from .schemas import (
    Event,
    IndexedClaim,
    IndexedClaimEvidence,
    IndexedEntity,
    IndexedEvent,
)
from .wiki_io import (
    WikiState,
    event_fingerprint,
    fw_dir,
)


def events_path(project_root: Path, case_id: str) -> Path:
    return fw_dir(project_root, case_id) / "events.json"


def entities_path(project_root: Path, case_id: str) -> Path:
    return fw_dir(project_root, case_id) / "entities.json"


def claims_path(project_root: Path, case_id: str) -> Path:
    return fw_dir(project_root, case_id) / "claims.json"


# --------------------------------------------------------------------------- #
# ID assignment — mutates state.id_counters / state.*_ids
# --------------------------------------------------------------------------- #


def assign_ids(state: WikiState) -> None:
    """Ensure every event / entity / hypothesis has a stable ID.

    New items get the next sequential ID; existing items keep theirs.
    """
    # Events
    for ev in state.events:
        fp = event_fingerprint(ev)
        if fp not in state.event_ids:
            state.event_ids[fp] = state.next_id("event")

    # Entities
    for key in state.entities:
        if key not in state.entity_ids:
            state.entity_ids[key] = state.next_id("entity")

    # Claims (hypotheses)
    for key in state.hypotheses:
        if key not in state.claim_ids:
            state.claim_ids[key] = state.next_id("claim")


# --------------------------------------------------------------------------- #
# Build the three index payloads
# --------------------------------------------------------------------------- #


def build_events(state: WikiState) -> list[IndexedEvent]:
    out: list[IndexedEvent] = []
    for ev in state.events:
        out.append(IndexedEvent(
            event_id=state.event_ids.get(event_fingerprint(ev), "evt_????"),
            timestamp=ev.timestamp or "unknown",
            event_type=_infer_event_type(ev),
            description=ev.description,
            source_path=ev.citation.target,
            evidence_text=ev.description,
            confidence="Medium",
        ))
    out.sort(key=lambda e: e.event_id)
    return out


def build_entities(state: WikiState) -> list[IndexedEntity]:
    out: list[IndexedEntity] = []
    for key, e in state.entities.items():
        related = []
        if any(_entity_appears_in_ioc(e, ioc) for ioc in state.iocs.values()):
            related.append("iocs.md")
        if any(_entity_appears_in_hypothesis(e, h) for h in state.hypotheses.values()):
            related.append("hypotheses.md")
        out.append(IndexedEntity(
            entity_id=state.entity_ids.get(key, "ent_????"),
            entity_type=e.type,
            value=e.value,
            source_paths=sorted({c.target for c in e.citations if c.kind == "source"}),
            related_pages=sorted({"entities.md", *related}),
        ))
    out.sort(key=lambda e: e.entity_id)
    return out


def build_claims(state: WikiState) -> list[IndexedClaim]:
    out: list[IndexedClaim] = []
    # Hypotheses become claims.
    for key, h in state.hypotheses.items():
        out.append(IndexedClaim(
            claim_id=state.claim_ids.get(key, "claim_????"),
            claim_type="hypothesis",
            claim_text=h.title + (f": {h.inference}" if h.inference else ""),
            confidence=h.confidence,
            supporting_evidence=[
                IndexedClaimEvidence(
                    source_path=_extract_source_path(s),
                    evidence_text=s,
                )
                for s in h.supporting_evidence
                if _extract_source_path(s)
            ],
            contradicting_evidence=_collect_contradicting_for_hypothesis(state, h),
            linked_pages=["hypotheses.md"] + (
                ["contradictions.md"] if _has_related_contradiction(state, h) else []
            ),
        ))
    out.sort(key=lambda c: c.claim_id)
    return out


# --------------------------------------------------------------------------- #
# Writers
# --------------------------------------------------------------------------- #


def write_indexes(project_root: Path, state: WikiState) -> dict[str, Path]:
    fw_dir(project_root, state.case_id).mkdir(parents=True, exist_ok=True)
    events = [e.model_dump() for e in build_events(state)]
    entities = [e.model_dump() for e in build_entities(state)]
    claims = [c.model_dump() for c in build_claims(state)]

    ep = events_path(project_root, state.case_id)
    np = entities_path(project_root, state.case_id)
    cp = claims_path(project_root, state.case_id)
    ep.write_text(json.dumps(events, indent=2))
    np.write_text(json.dumps(entities, indent=2))
    cp.write_text(json.dumps(claims, indent=2))
    return {"events.json": ep, "entities.json": np, "claims.json": cp}


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


_PROCESS_KEYWORDS = ("spawn", "powershell command", "cmd.exe")
_NETWORK_KEYWORDS = ("connect", "outbound", "tcp", "udp")
_REGISTRY_KEYWORDS = ("registry value",)
_SCAN_KEYWORDS = ("defender", "scan")
_NOTE_KEYWORDS = ("investigator note",)


def _infer_event_type(ev: Event) -> str:
    desc = ev.description.lower()
    if any(k in desc for k in _PROCESS_KEYWORDS):
        return "process_execution"
    if any(k in desc for k in _NETWORK_KEYWORDS):
        return "network_connection"
    if any(k in desc for k in _REGISTRY_KEYWORDS):
        return "registry_change"
    if any(k in desc for k in _SCAN_KEYWORDS):
        return "av_scan"
    if any(k in desc for k in _NOTE_KEYWORDS):
        return "investigator_note"
    return "other"


def _entity_appears_in_ioc(entity, ioc) -> bool:
    return entity.value.lower() in (ioc.artifact + " " + ioc.reason).lower()


def _entity_appears_in_hypothesis(entity, hyp) -> bool:
    blob = " ".join(hyp.facts + [hyp.inference] + hyp.supporting_evidence)
    return entity.value.lower() in blob.lower()


def _extract_source_path(s: str) -> str:
    import re
    m = re.search(r"raw_sources/\S+", s)
    if not m:
        return ""
    # Trim trailing punctuation.
    return m.group(0).rstrip(").,;")


_LINK_STOPWORDS = {
    "the", "a", "an", "of", "to", "and", "or", "in", "on", "for", "with",
    "by", "as", "is", "are", "was", "were", "be", "been", "this", "that",
    "vs", "vs.", "from", "into", "any", "limited", "objective",
}


def _tokens(s: str) -> set[str]:
    return {
        t for t in s.lower().replace("/", " ").replace(".", " ").split()
        if t and t not in _LINK_STOPWORDS and len(t) > 2
    }


def _has_related_contradiction(state, h) -> bool:
    htoks = _tokens(h.title) | _tokens(h.inference)
    htoks |= {tok for f in h.facts for tok in _tokens(f)}
    for c in state.contradictions.values():
        ctoks = _tokens(c.title) | _tokens(c.claim_a) | _tokens(c.claim_b)
        if htoks & ctoks:
            return True
    return False


def _collect_contradicting_for_hypothesis(state, h) -> list[IndexedClaimEvidence]:
    out: list[IndexedClaimEvidence] = []
    seen: set[tuple[str, str]] = set()
    for s in h.contradicting_evidence:
        sp = _extract_source_path(s)
        if sp and (sp, s) not in seen:
            out.append(IndexedClaimEvidence(source_path=sp, evidence_text=s))
            seen.add((sp, s))

    htoks = _tokens(h.title) | _tokens(h.inference)
    htoks |= {tok for f in h.facts for tok in _tokens(f)}
    for c in state.contradictions.values():
        ctoks = _tokens(c.title) | _tokens(c.claim_a) | _tokens(c.claim_b)
        if not (htoks & ctoks):
            continue
        sp = _extract_source_path(c.claim_b)
        if sp and (sp, c.claim_b) not in seen:
            out.append(IndexedClaimEvidence(source_path=sp, evidence_text=c.claim_b))
            seen.add((sp, c.claim_b))
    return out
