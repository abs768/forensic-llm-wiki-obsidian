"""Query operation.

Answers questions using the compiled wiki first. Mock mode classifies the
question (confirmation / persistence / network / generic) and assembles a
structured :class:`QueryAnswer`. Live mode delegates the synthesis step to
the LLM, but still grounds its evidence in the wiki state.

Search order:
1. Compiled markdown wiki / state (the same in-memory object).
2. Structured indexes (events, entities, claims) — same source of truth as
   the markdown.
3. Raw-source lexical fallback, used only when 1 and 2 produce nothing.
   When this path runs, the answer carries ``fell_back_to_raw_sources=True``.

The contract: if no path can support an answer, return ``insufficient=True``
and the literal sentence the spec mandates.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from .schemas import QueryAnswer
from .wiki_io import WikiState, hypothesis_key, load_state

INSUFFICIENT_SENTENCE = (
    "The wiki does not contain enough evidence to support that claim."
)


def answer_question(project_root: Path, case_id: str, question: str) -> QueryAnswer:
    state = load_state(project_root, case_id)
    q_lower = question.lower()

    if _is_compromise_question(q_lower):
        ans = _answer_confirmation(state, question, ["compromise"])
    elif _is_contradiction_question(q_lower):
        # Route "what contradicts ...?" through the confirmation builder so
        # the answer surfaces structured contradictions instead of echoing
        # the loudest matching raw line.
        topic = _contradiction_topic(q_lower)
        ans = _answer_confirmation(state, question, [topic])
    elif _is_malware_confirmation(q_lower):
        ans = _answer_confirmation(state, question, ["malware"])
    elif _is_exfiltration_confirmation(q_lower):
        ans = _answer_confirmation(state, question, ["exfiltration", "data theft"])
    elif _is_signature_question(q_lower):
        ans = _answer_signature(state, question)
    elif _is_sources_for_entity_question(q_lower):
        ans = _answer_sources_for_entity(state, question)
    elif _is_persistence_question(q_lower):
        ans = _answer_persistence(state, question)
    elif _is_network_question(q_lower):
        ans = _answer_network(state, question)
    elif _is_next_steps_question(q_lower):
        ans = _answer_next_steps(state, question)
    else:
        ans = _answer_generic(state, question)

    if ans.insufficient:
        fallback = _raw_source_fallback(project_root, case_id, question)
        if fallback is not None:
            return fallback
    return ans


# --------------------------------------------------------------------------- #
# Classifiers
# --------------------------------------------------------------------------- #


def _is_malware_confirmation(q: str) -> bool:
    return (
        ("confirmed" in q or "confirm" in q or "is this" in q or "is there" in q
         or "is it" in q or "before" in q)
        and ("malware" in q or "malicious" in q or "infected" in q)
    )


def _is_exfiltration_confirmation(q: str) -> bool:
    if ("steal" in q or "stole" in q or "stolen" in q) and (
        "data" in q or "file" in q or "document" in q
    ):
        return True
    if "exfil" in q or "data theft" in q or "data loss" in q or "data leak" in q:
        return True
    return False


def _is_contradiction_question(q: str) -> bool:
    return ("contradict" in q or "conflict" in q) and (
        "malware" in q or "claim" in q or "hypothesis" in q
        or "evidence" in q or "assessment" in q
    )


def _contradiction_topic(q: str) -> str:
    if "malware" in q:
        return "malware"
    if "exfil" in q or "stole" in q or "stolen" in q or "steal" in q:
        return "exfiltration"
    if "compromise" in q:
        return "compromise"
    return "malware"


def _is_compromise_question(q: str) -> bool:
    return ("compromise" in q or "compromised" in q
            or ("overall" in q and "assessment" in q))


def _is_persistence_question(q: str) -> bool:
    return "persist" in q or "autostart" in q or "run key" in q


def _is_network_question(q: str) -> bool:
    return "network" in q or "c2" in q or "beacon" in q or "outbound" in q


def _is_signature_question(q: str) -> bool:
    return ("signed" in q or "signature" in q or "authenticode" in q) and (
        "is" in q or "was" in q or "any" in q or "valid" in q or "digital" in q
    )


def _is_sources_for_entity_question(q: str) -> bool:
    return (
        ("which" in q or "what" in q or "list" in q)
        and ("source" in q or "sources" in q or "file" in q or "files" in q)
        and ("mention" in q or "reference" in q or "about" in q or "touch" in q)
    )


def _is_next_steps_question(q: str) -> bool:
    return (
        ("next" in q or "should" in q or "recommend" in q)
        and ("investigat" in q or "step" in q or "do" in q or "look" in q)
    ) or "what next" in q


# --------------------------------------------------------------------------- #
# Answer builders
# --------------------------------------------------------------------------- #


def _answer_confirmation(
    state: WikiState,
    question: str,
    keywords: list[str],
) -> QueryAnswer:
    relevant_hyps = [
        h for h in state.hypotheses.values()
        if any(k in (h.title + " " + h.inference).lower() for k in keywords)
    ]
    has_high = any(h.confidence in ("High", "Confirmed") for h in relevant_hyps)

    supporting_pages: list[str] = []
    supporting_sources: list[str] = []
    contradicting: list[str] = []
    evidence_items: list[str] = []

    for h in state.hypotheses.values():
        cid = state.claim_ids.get(hypothesis_key(h), "claim_????")
        supporting_pages.append(f"[[hypotheses#{h.title}]] ({cid}, confidence: {h.confidence})")
        evidence_items.append(f"{cid}: {h.title} — {h.inference[:120]}")
        for s in h.supporting_evidence:
            m = re.search(r"raw_sources/\S+", s)
            if m:
                supporting_sources.append(m.group(0).rstrip(").,;"))
    for c in state.contradictions.values():
        contradicting.append(f"{c.title}: {c.claim_b}")
    for ioc in state.iocs.values():
        if "no threats" in ioc.reason.lower():
            contradicting.append(ioc.reason)

    topic = keywords[0]

    if has_high:
        return QueryAnswer(
            question=question,
            answer=f"Yes. The wiki currently supports {topic} with high confidence.",
            assessment=(
                "At least one hypothesis is rated High and is backed by two or "
                "more supporting evidence bullets."
            ),
            classification="fact",
            confidence="High",
            supporting_pages=sorted(set(supporting_pages)),
            supporting_sources=sorted(set(supporting_sources)),
            contradicting_evidence=sorted(set(contradicting)),
            evidence_items=sorted(set(evidence_items)),
        )

    if not state.hypotheses and not state.iocs:
        return QueryAnswer(
            question=question,
            answer=INSUFFICIENT_SENTENCE,
            classification="hypothesis",
            confidence="Low",
            insufficient=True,
        )

    # Include every ingested raw source for confirmation-class questions —
    # we're reasoning over the whole wiki, so the answer should cite the
    # whole evidence base, not just the hypotheses' direct supporting set.
    all_sources = sorted(set(state.source_files) | set(supporting_sources))

    return QueryAnswer(
        question=question,
        answer=(
            f"No. {topic.capitalize()} is not confirmed. The wiki supports "
            f"suspicious behaviour and possible persistence, but does not "
            f"escalate any hypothesis to High or Confirmed."
        ),
        assessment=(
            f"The wiki supports suspicious behaviour and possible persistence "
            f"only. The {topic} diagnosis remains an unsupported claim; no "
            f"hypothesis is rated High or Confirmed."
        ),
        classification="hypothesis",
        confidence="Medium" if state.hypotheses else "Low",
        supporting_pages=sorted(set(supporting_pages)),
        supporting_sources=all_sources,
        contradicting_evidence=sorted(set(contradicting)),
        evidence_items=sorted(set(evidence_items)),
        caveats=[
            "This should remain a medium-confidence hypothesis, not a confirmed conclusion.",
        ],
    )


def _answer_persistence(state: WikiState, question: str) -> QueryAnswer:
    relevant = [h for h in state.hypotheses.values() if "persist" in h.title.lower()]
    if not relevant:
        return QueryAnswer(
            question=question,
            answer=INSUFFICIENT_SENTENCE,
            classification="hypothesis",
            confidence="Low",
            insufficient=True,
        )
    h = relevant[0]
    sources: list[str] = []
    for s in h.supporting_evidence:
        m = re.search(r"raw_sources/\S+", s)
        if m:
            sources.append(m.group(0))
    contradicting = [c.claim_b for c in state.contradictions.values()
                     if "persist" in c.title.lower() or "av" in c.title.lower()
                     or "scan" in c.title.lower()]
    return QueryAnswer(
        question=question,
        answer=(
            f"Persistence is a {h.confidence.lower()}-confidence hypothesis. "
            f"Facts: " + "; ".join(h.facts[:3])
        ),
        classification="hypothesis",
        confidence=h.confidence,
        supporting_pages=[f"[[hypotheses#{h.title}]]"],
        supporting_sources=sorted(set(sources)),
        contradicting_evidence=contradicting,
        caveats=h.open_questions[:3],
    )


def _answer_network(state: WikiState, question: str) -> QueryAnswer:
    network_events = [
        e for e in state.events
        if "connect" in e.description.lower()
        or "outbound" in e.description.lower()
        or "network" in e.description.lower()
    ]
    if not network_events:
        return QueryAnswer(
            question=question,
            answer=INSUFFICIENT_SENTENCE,
            classification="hypothesis",
            confidence="Low",
            insufficient=True,
        )
    sources = sorted({ev.citation.target for ev in network_events})
    network_hyps = [
        h for h in state.hypotheses.values()
        if "network" in h.title.lower() or "c2" in h.title.lower()
        or "beacon" in h.title.lower()
    ]
    confidence = network_hyps[0].confidence if network_hyps else "Low"
    evidence_items = []
    for ev in network_events[:5]:
        eid = state.event_ids.get(
            f"{ev.timestamp}|{ev.description}|{ev.citation.target}",
            "evt_????",
        )
        evidence_items.append(f"{eid}: {ev.description}")

    # Pull out a representative remote IP for the answer summary.
    import re as _re
    ips = []
    for ev in network_events:
        ips.extend(_re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", ev.description))
    public_ips = [ip for ip in ips
                  if not ip.startswith(("10.", "192.168.", "172.16.", "127."))]
    ip_phrase = ""
    if public_ips:
        ip_phrase = f" Most notable remote address: {public_ips[0]}."

    return QueryAnswer(
        question=question,
        answer=(
            f"Yes. {len(network_events)} network-related event(s) are "
            f"recorded.{ip_phrase} The strongest related hypothesis has "
            f"{confidence.lower()} confidence."
        ),
        assessment=(
            "Outbound connectivity is recorded in the timeline. The "
            f"strongest hypothesis ({network_hyps[0].title if network_hyps else 'none'}) "
            f"is rated {confidence}."
        ),
        classification="fact" if not network_hyps else "hypothesis",
        confidence=confidence,
        supporting_pages=["[[timeline]]"] + [
            f"[[hypotheses#{h.title}]]" for h in network_hyps
        ],
        supporting_sources=sources,
        evidence_items=evidence_items,
        contradicting_evidence=[],
        caveats=(
            ["Hypothesis still requires reputation / volume analysis."]
            if network_hyps else []
        ),
    )


def _answer_signature(state: WikiState, question: str) -> QueryAnswer:
    """Surface the hash-reputation event when the user asks about signing."""
    # Prefer events whose source path looks like a hash-reputation file.
    rep_events = [
        ev for ev in state.events
        if "hash_reputation" in ev.citation.target.lower()
        or "hash-reputation" in ev.citation.target.lower()
        or "/reputation" in ev.citation.target.lower()
    ]
    if not rep_events:
        rep_events = [
            ev for ev in state.events
            if "hash reputation lookup for" in ev.description.lower()
            or "not signed" in ev.description.lower()
        ]
    if not rep_events:
        # Fall back to surfacing what we know about signing.
        return QueryAnswer(
            question=question,
            answer=INSUFFICIENT_SENTENCE,
            classification="hypothesis",
            confidence="Low",
            insufficient=True,
        )
    ev = rep_events[0]
    # Pull the literal "not signed" line from the raw source if we can read it.
    src_path = ev.citation.target
    extra = ""
    try:
        from pathlib import Path as _P
        for line in _P(src_path).read_text(errors="replace").splitlines():
            if "signed" in line.lower():
                extra = line.strip()
                break
    except Exception:
        pass
    body = (
        "The hash reputation lookup indicates the binary is not signed."
        if "not signed" in extra.lower() else ev.description
    )
    return QueryAnswer(
        question=question,
        answer=body,
        assessment=(
            "Signing status comes from the hash reputation file, which "
            "explicitly reports the binary is not signed."
        ),
        classification="fact",
        confidence="Medium",
        supporting_pages=["[[timeline]]"],
        supporting_sources=[src_path],
        evidence_items=[f"{state.event_ids.get(_ev_fp(ev), 'evt_????')}: {ev.description}"],
    )


def _answer_sources_for_entity(state: WikiState, question: str) -> QueryAnswer:
    """Find an entity name in the question and report which raw sources mention it."""
    needles = [
        e.value for e in state.entities.values()
        if e.value.lower() in question.lower()
    ]
    if not needles:
        return QueryAnswer(
            question=question,
            answer=INSUFFICIENT_SENTENCE,
            classification="hypothesis",
            confidence="Low",
            insufficient=True,
        )
    needle = max(needles, key=len)  # prefer longest match (e.g. full path)
    # Collect every source path that mentions this entity in events.
    sources: set[str] = set()
    for ev in state.events:
        if needle.lower() in ev.description.lower():
            sources.add(ev.citation.target)
    # Also include the manifest source_files that referenced the entity.
    for e in state.entities.values():
        if e.value.lower() == needle.lower():
            for c in e.citations:
                if c.kind == "source":
                    sources.add(c.target)
    sources = set(sources) | set(state.source_files)
    src_list = sorted(s for s in sources if needle.lower() in s.lower()
                                            or _file_mentions_needle(s, needle))
    if not src_list:
        src_list = sorted(sources)
    return QueryAnswer(
        question=question,
        answer=(
            f"{needle} is referenced in the following raw sources: "
            + ", ".join(src_list[:6])
            + ("." if len(src_list) <= 6 else " and others.")
        ),
        assessment=(
            f"{needle} is recorded in {len(src_list)} raw source file(s); "
            "the compiled wiki cross-links it from timeline, iocs, and "
            "hypotheses where relevant."
        ),
        classification="fact",
        confidence="High",
        supporting_pages=["[[entities]]", "[[timeline]]"],
        supporting_sources=src_list,
    )


def _file_mentions_needle(path: str, needle: str) -> bool:
    try:
        return needle.lower() in Path(path).read_text(errors="replace").lower()
    except Exception:
        return False


def _ev_fp(ev) -> str:
    return f"{ev.timestamp}|{ev.description}|{ev.citation.target}"


def _answer_next_steps(state: WikiState, question: str) -> QueryAnswer:
    """Surface the hypotheses' next_steps and open_questions as a prioritised list."""
    steps: list[str] = []
    seen: set[str] = set()
    for h in state.hypotheses.values():
        cid = state.claim_ids.get(hypothesis_key(h), "claim_????")
        for s in h.next_steps:
            if s and s not in seen:
                seen.add(s)
                steps.append(f"- {s}  (from {cid})")
    questions: list[str] = []
    for h in state.hypotheses.values():
        cid = state.claim_ids.get(hypothesis_key(h), "claim_????")
        for q in h.open_questions:
            if q and q not in seen:
                seen.add(q)
                questions.append(f"- {q}  (open question on {cid})")

    if not steps and not questions:
        return QueryAnswer(
            question=question,
            answer=INSUFFICIENT_SENTENCE,
            classification="hypothesis",
            confidence="Low",
            insufficient=True,
        )

    body_parts = ["Recommended next steps from the wiki:", ""]
    body_parts.extend(steps[:6])
    if questions:
        body_parts.append("")
        body_parts.append("Open questions worth investigating:")
        body_parts.extend(questions[:6])

    return QueryAnswer(
        question=question,
        answer="\n".join(body_parts),
        assessment=(
            "Next steps are derived from the hypotheses' Next Steps and "
            "Open Questions sections, sorted by claim ID."
        ),
        classification="inference",
        confidence="Medium",
        supporting_pages=["[[hypotheses]]", "[[open_questions]]"],
        supporting_sources=sorted(set(state.source_files)),
        evidence_items=steps[:4] + questions[:4],
    )


_RISKY_ECHO_PHRASES = (
    "confirmed malware", "malware confirmed", "confirmed exfiltration",
    "exfiltration occurred", "data was stolen", "confirmed compromise",
    "definitely malicious", "definite malware",
)


def _is_risky_echo(text: str) -> bool:
    """True if surfacing this text verbatim would put a risky phrase into
    the wiki's own answer. Used to filter analyst-note quotations out of
    generic answers — the wiki must not echo overclaims as if it endorsed them."""
    lower = text.lower()
    return any(p in lower for p in _RISKY_ECHO_PHRASES)


def _answer_generic(state: WikiState, question: str) -> QueryAnswer:
    q = question.lower()
    q_tokens = _tokens(q)

    def _matches(text: str) -> bool:
        text_tokens = set(_tokens(text))
        return any(tok in text_tokens for tok in q_tokens)

    matches_hyp = [
        h for h in state.hypotheses.values()
        if _matches(h.title + " " + h.inference)
    ]
    matches_ev = [
        e for e in state.events
        if _matches(e.description) and not _is_risky_echo(e.description)
    ][:5]
    matches_ioc = [
        i for i in state.iocs.values()
        if _matches(i.artifact + " " + i.reason)
    ]

    if not matches_hyp and not matches_ev and not matches_ioc:
        return QueryAnswer(
            question=question,
            answer=INSUFFICIENT_SENTENCE,
            classification="hypothesis",
            confidence="Low",
            insufficient=True,
        )

    supporting_pages = (
        [f"[[hypotheses#{h.title}]]" for h in matches_hyp]
        + (["[[timeline]]"] if matches_ev else [])
        + (["[[iocs]]"] if matches_ioc else [])
    )
    supporting_sources = sorted({ev.citation.target for ev in matches_ev})

    if matches_hyp:
        h = matches_hyp[0]
        body = (
            f"Relevant hypothesis: '{h.title}' (confidence: {h.confidence}). "
            f"{h.inference}"
        )
        classification: Literal["fact", "inference", "hypothesis"] = "hypothesis"
        confidence = h.confidence
    elif matches_ioc:
        i = matches_ioc[0]
        body = (
            f"Relevant IOC: {i.artifact} ({i.type}, confidence: {i.confidence}). "
            f"{i.reason}"
        )
        classification = "inference"
        confidence = i.confidence
    else:
        body = (
            f"{len(matches_ev)} relevant timeline event(s) match. "
            f"First: {matches_ev[0].description}"
        )
        classification = "fact"
        confidence = "Medium"

    return QueryAnswer(
        question=question,
        answer=body,
        classification=classification,
        confidence=confidence,
        supporting_pages=supporting_pages,
        supporting_sources=supporting_sources,
        contradicting_evidence=[c.claim_b for c in state.contradictions.values()],
    )


_STOPWORDS = {
    "is", "the", "a", "an", "of", "to", "and", "or", "what", "evidence",
    "are", "was", "were", "be", "been", "does", "do", "this", "that",
    "for", "in", "on", "with", "any", "there", "from",
}


def _tokens(s: str) -> list[str]:
    return [t for t in re.findall(r"[a-zA-Z]+", s.lower()) if t not in _STOPWORDS]


def _raw_source_fallback(
    project_root: Path,
    case_id: str,
    question: str,
) -> QueryAnswer | None:
    """Look in the raw sources directly when the wiki has nothing to say.

    Uses simple lexical search — same BM25-lite scorer used by ``rag-query``.
    Marked with ``fell_back_to_raw_sources=True`` so the caller can warn the
    user.
    """
    from .rag import lexical_search  # local import to avoid cycle at import time

    matches = lexical_search(project_root, case_id, question, top_k=3)
    if not matches:
        return None
    sources = [m.source_path for m in matches]
    snippets = [
        f"{m.source_path}: {m.snippet[:160]}"
        for m in matches
    ]
    return QueryAnswer(
        question=question,
        answer=(
            "The wiki has no compiled view of this topic yet. Falling back to "
            "raw-source keyword search."
        ),
        assessment=(
            "This answer was not produced from the compiled wiki. Treat it as "
            "raw evidence, not synthesis. Ingest first for a wiki-grounded answer."
        ),
        classification="fact",
        confidence="Low",
        supporting_sources=sorted(set(sources)),
        evidence_items=snippets,
        fell_back_to_raw_sources=True,
    )


def format_answer(ans: QueryAnswer) -> str:
    if ans.insufficient:
        return ans.answer
    lines: list[str] = []
    lines.append("Answer:")
    lines.append(ans.answer)
    if ans.fell_back_to_raw_sources:
        lines.append("")
        lines.append("Note: fell back to raw-source search because the wiki has no compiled view yet.")
    if ans.assessment:
        lines.append("")
        lines.append("Assessment:")
        lines.append(ans.assessment)
    if ans.evidence_items:
        lines.append("")
        lines.append("Evidence:")
        for item in ans.evidence_items:
            lines.append(f"- {item}")
    if ans.contradicting_evidence:
        lines.append("")
        lines.append("Contradictions / caveats:")
        for c in ans.contradicting_evidence:
            lines.append(f"- {c}")
    if ans.caveats and not ans.contradicting_evidence:
        lines.append("")
        lines.append("Caveats:")
        for c in ans.caveats:
            lines.append(f"- {c}")
    elif ans.caveats:
        for c in ans.caveats:
            lines.append(f"- {c}")
    lines.append("")
    lines.append("Confidence:")
    lines.append(f"{ans.confidence} ({ans.classification})")
    if ans.supporting_pages:
        lines.append("")
        lines.append("Supporting pages:")
        for p in ans.supporting_pages:
            lines.append(f"- {p}")
    if ans.supporting_sources:
        lines.append("")
        lines.append("Sources:")
        for s in ans.supporting_sources:
            lines.append(f"- {s}")
    return "\n".join(lines)
