"""Naive raw-source RAG baseline.

This deliberately resembles the kind of "ask my docs" pipeline that the
Forensic LLM Wiki is meant to outperform on synthesis/contradiction
questions. It does:

1. Tokenise raw source files (lowercase alphanumerics).
2. Compute a BM25-ish score per (document, query) pair.
3. Return the top-K matching documents with the highest-scoring snippet.
4. Compose an answer that simply concatenates the top snippets.

There is no vector index, no embedding model, no LLM call. The point is to
show what a "search files every time" system can — and cannot — do.

Critically, the baseline has no contradictions ledger and no compiled
hypotheses. Asking "Is this confirmed malware?" against the demo case will
pull the investigator-note line that says "possible malware infection" and
the AV-clean line and present both raw, without synthesis. The compiled
wiki, by contrast, has already reconciled these into a Medium-confidence
hypothesis with explicit contradictions.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from .schemas import QueryAnswer
from .wiki_io import raw_case_dir

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_.\-]*")
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "of", "to", "and", "or", "in", "on", "for", "with", "by", "as",
    "this", "that", "these", "those", "any", "from", "into", "what",
    "which", "who", "whom", "whose", "do", "does", "did", "has", "have",
    "had", "it", "its", "his", "her", "their", "our", "your", "my",
    "we", "you", "they", "i", "if", "when", "where", "why", "how",
}


def _tokenise(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text) if t.lower() not in _STOPWORDS]


@dataclass
class RagMatch:
    source_path: str  # relative to project root
    score: float
    snippet: str
    matched_terms: list[str] = field(default_factory=list)


@dataclass
class RagCorpus:
    project_root: Path
    case_id: str
    docs: dict[str, list[str]]            # rel_path -> tokens
    lines_by_path: dict[str, list[str]]   # rel_path -> raw lines
    df: dict[str, int]                    # term -> doc frequency
    n_docs: int


def build_corpus(project_root: Path, case_id: str) -> RagCorpus:
    raw_dir = raw_case_dir(project_root, case_id)
    docs: dict[str, list[str]] = {}
    lines_by_path: dict[str, list[str]] = {}
    df: dict[str, int] = {}

    if raw_dir.exists():
        for path in sorted(raw_dir.rglob("*")):
            if not path.is_file():
                continue
            if any(part.startswith(".") for part in path.relative_to(raw_dir).parts):
                continue
            rel = str(path.relative_to(project_root))
            text = path.read_text(encoding="utf-8", errors="replace")
            tokens = _tokenise(text)
            docs[rel] = tokens
            lines_by_path[rel] = text.splitlines()
            for t in set(tokens):
                df[t] = df.get(t, 0) + 1

    return RagCorpus(
        project_root=project_root,
        case_id=case_id,
        docs=docs,
        lines_by_path=lines_by_path,
        df=df,
        n_docs=len(docs),
    )


def lexical_search(
    project_root: Path,
    case_id: str,
    query: str,
    *,
    top_k: int = 5,
    corpus: RagCorpus | None = None,
) -> list[RagMatch]:
    corpus = corpus or build_corpus(project_root, case_id)
    if corpus.n_docs == 0:
        return []
    q_tokens = _tokenise(query)
    if not q_tokens:
        return []

    # BM25 parameters
    k1, b = 1.5, 0.75
    avgdl = sum(len(d) for d in corpus.docs.values()) / max(1, corpus.n_docs)

    scored: list[RagMatch] = []
    for rel, tokens in corpus.docs.items():
        dl = max(1, len(tokens))
        tf_counts: dict[str, int] = {}
        for t in tokens:
            tf_counts[t] = tf_counts.get(t, 0) + 1

        score = 0.0
        matched: set[str] = set()
        for q in q_tokens:
            tf = tf_counts.get(q, 0)
            if tf == 0:
                continue
            matched.add(q)
            n = corpus.df.get(q, 0)
            idf = math.log(1 + (corpus.n_docs - n + 0.5) / (n + 0.5))
            denom = tf + k1 * (1 - b + b * dl / avgdl)
            score += idf * tf * (k1 + 1) / denom
        if score <= 0:
            continue
        snippet = _best_snippet(corpus.lines_by_path[rel], q_tokens)
        scored.append(RagMatch(
            source_path=rel,
            score=score,
            snippet=snippet,
            matched_terms=sorted(matched),
        ))

    scored.sort(key=lambda m: m.score, reverse=True)
    return scored[:top_k]


def _best_snippet(lines: list[str], q_tokens: list[str]) -> str:
    qset = set(q_tokens)
    best_line = ""
    best_hits = -1
    for line in lines:
        toks = set(_tokenise(line))
        hits = len(qset & toks)
        if hits > best_hits and line.strip():
            best_hits = hits
            best_line = line.strip()
    return best_line


# --------------------------------------------------------------------------- #
# Public rag_query — used by the CLI
# --------------------------------------------------------------------------- #


def rag_query(project_root: Path, case_id: str, question: str, top_k: int = 5) -> QueryAnswer:
    matches = lexical_search(project_root, case_id, question, top_k=top_k)
    if not matches:
        return QueryAnswer(
            question=question,
            answer=(
                "No raw-source lines match the query terms. The raw-source "
                "baseline has nothing to retrieve."
            ),
            classification="fact",
            confidence="Low",
            insufficient=True,
            fell_back_to_raw_sources=True,
        )
    answer_body = _compose_naive_answer(question, matches)
    return QueryAnswer(
        question=question,
        answer=answer_body,
        assessment=(
            "Generated by naive lexical retrieval over raw_sources/. No "
            "synthesis, no contradiction handling, no hypothesis tracking. "
            "This is the 'ask my docs' baseline."
        ),
        classification="fact",
        confidence="Low",
        supporting_sources=[m.source_path for m in matches],
        evidence_items=[f"{m.source_path} (score={m.score:.2f}): {m.snippet[:160]}"
                        for m in matches],
        fell_back_to_raw_sources=True,
    )


def _compose_naive_answer(question: str, matches: list[RagMatch]) -> str:
    """The hallmark of naive RAG: state what the docs say, no synthesis.

    For the malware question, this will faithfully reproduce both the
    investigator's "possible malware" line and the AV "no threats" line
    next to each other, without reconciling them — exactly the failure
    mode the compiled wiki avoids.
    """
    q_lower = question.lower()
    top_snippets = "\n".join(f"- {m.source_path}: {m.snippet}" for m in matches)
    if "malware" in q_lower or "confirmed" in q_lower:
        return (
            "Based on raw_sources/ keyword hits, the most relevant lines are "
            "shown below. The baseline does not reconcile conflicting "
            "evidence.\n\n" + top_snippets
        )
    if "persist" in q_lower:
        return (
            "Top raw-source matches for persistence-related terms:\n\n"
            + top_snippets
        )
    return (
        "Top raw-source matches for the query terms:\n\n" + top_snippets
    )
