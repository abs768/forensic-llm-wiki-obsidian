"""Vector-RAG baseline: embedding retrieval over chunked raw sources.

This is the stronger retrieval baseline the lexical one is often accused
of strawmanning. It does:

1. Split raw source files into small line-window chunks.
2. Embed every chunk and the query.
3. Rank chunks by cosine similarity and return the top-K.
4. Compose an answer that concatenates the top chunks' best lines.

Like the lexical baseline, it deliberately stops there: no synthesis, no
contradictions ledger, no compiled hypotheses, no refusal discipline.
Better retrieval changes *which* snippets come back, not what the system
does with them — that gap is the point of the comparison.

Embedding backends (selected via ``FORENSIC_WIKI_EMBEDDINGS``):

- ``hash`` (default) — a deterministic hashed bag-of-words embedder with
  no dependencies. It keeps tests and CI reproducible without a model
  download, but it is still lexical at heart.
- ``local`` — dense semantic embeddings via ``sentence-transformers``
  (install with ``pip install -e ".[vector]"``). Used to produce the
  committed scorecards.
"""
from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass, field
from pathlib import Path

from .rag import _best_snippet, _tokenise
from .schemas import QueryAnswer
from .wiki_io import raw_case_dir

_CHUNK_LINES = 8
_CHUNK_OVERLAP = 2
_HASH_DIMS = 256

_ENV_BACKEND = "FORENSIC_WIKI_EMBEDDINGS"
_ENV_MODEL = "FORENSIC_WIKI_EMBED_MODEL"
_DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


# --------------------------------------------------------------------------- #
# Embedding backends
# --------------------------------------------------------------------------- #


class HashingEmbedder:
    """Deterministic hashed bag-of-words embedding.

    Tokens (and adjacent-token bigrams) are hashed into a fixed number of
    signed dimensions via md5, weighted by ``1 + log(tf)``, then
    L2-normalised. Same text always produces the same vector, on any
    machine, with no dependencies — which is what CI needs.
    """

    name = "hash (deterministic bag-of-words)"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        tokens = _tokenise(text)
        grams = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:], strict=False)]
        tf: dict[str, int] = {}
        for g in grams:
            tf[g] = tf.get(g, 0) + 1

        vec = [0.0] * _HASH_DIMS
        for g, count in tf.items():
            digest = hashlib.md5(g.encode()).digest()
            idx = int.from_bytes(digest[:4], "little") % _HASH_DIMS
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign * (1.0 + math.log(count))

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


class SentenceTransformerEmbedder:
    """Dense semantic embeddings via sentence-transformers (optional)."""

    def __init__(self, model_name: str | None = None) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:  # pragma: no cover - exercised only without extra
            raise RuntimeError(
                "FORENSIC_WIKI_EMBEDDINGS=local requires sentence-transformers. "
                'Install it with: pip install -e ".[vector]"'
            ) from e
        self.model_name = model_name or os.environ.get(_ENV_MODEL, _DEFAULT_MODEL)
        self.name = self.model_name
        self._model = SentenceTransformer(self.model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [list(map(float, v)) for v in vectors]


def get_embedder() -> HashingEmbedder | SentenceTransformerEmbedder:
    backend = os.environ.get(_ENV_BACKEND, "hash").lower()
    if backend == "local":
        return SentenceTransformerEmbedder()
    return HashingEmbedder()


# --------------------------------------------------------------------------- #
# Chunking and retrieval
# --------------------------------------------------------------------------- #


@dataclass
class Chunk:
    source_path: str  # relative to project root
    text: str
    lines: list[str] = field(default_factory=list)


@dataclass
class VectorMatch:
    source_path: str
    score: float
    snippet: str


def build_chunks(project_root: Path, case_id: str) -> list[Chunk]:
    raw_dir = raw_case_dir(project_root, case_id)
    chunks: list[Chunk] = []
    if not raw_dir.exists():
        return chunks
    for path in sorted(raw_dir.rglob("*")):
        if not path.is_file():
            continue
        if any(part.startswith(".") for part in path.relative_to(raw_dir).parts):
            continue
        rel = str(path.relative_to(project_root))
        lines = [
            ln for ln in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if ln.strip()
        ]
        step = max(1, _CHUNK_LINES - _CHUNK_OVERLAP)
        for start in range(0, max(1, len(lines)), step):
            window = lines[start:start + _CHUNK_LINES]
            if not window:
                continue
            chunks.append(Chunk(source_path=rel, text="\n".join(window), lines=window))
            if start + _CHUNK_LINES >= len(lines):
                break
    return chunks


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=False))


def vector_search(
    project_root: Path,
    case_id: str,
    query: str,
    *,
    top_k: int = 5,
    embedder: HashingEmbedder | SentenceTransformerEmbedder | None = None,
) -> list[VectorMatch]:
    chunks = build_chunks(project_root, case_id)
    if not chunks:
        return []
    embedder = embedder or get_embedder()
    vectors = embedder.embed([c.text for c in chunks] + [query])
    chunk_vecs, q_vec = vectors[:-1], vectors[-1]

    q_tokens = _tokenise(query)
    scored: list[VectorMatch] = []
    for chunk, vec in zip(chunks, chunk_vecs, strict=True):
        score = _cosine(vec, q_vec)
        if score <= 0:
            continue
        scored.append(VectorMatch(
            source_path=chunk.source_path,
            score=score,
            snippet=_best_snippet(chunk.lines, q_tokens) or chunk.lines[0].strip(),
        ))
    scored.sort(key=lambda m: m.score, reverse=True)

    # Deduplicate by (source, snippet) so overlapping windows don't
    # crowd out other sources.
    seen: set[tuple[str, str]] = set()
    out: list[VectorMatch] = []
    for m in scored:
        key = (m.source_path, m.snippet)
        if key in seen:
            continue
        seen.add(key)
        out.append(m)
        if len(out) >= top_k:
            break
    return out


# --------------------------------------------------------------------------- #
# Public vector_rag_query — used by the CLI and benchmarks
# --------------------------------------------------------------------------- #


def vector_rag_query(
    project_root: Path,
    case_id: str,
    question: str,
    top_k: int = 5,
) -> QueryAnswer:
    embedder = get_embedder()
    matches = vector_search(
        project_root, case_id, question, top_k=top_k, embedder=embedder,
    )
    if not matches:
        return QueryAnswer(
            question=question,
            answer=(
                "No raw-source chunks are similar to the query. The vector "
                "baseline has nothing to retrieve."
            ),
            classification="fact",
            confidence="Low",
            insufficient=True,
            fell_back_to_raw_sources=True,
        )
    top_snippets = "\n".join(f"- {m.source_path}: {m.snippet}" for m in matches)
    return QueryAnswer(
        question=question,
        answer=(
            "Based on embedding-similarity over raw_sources/ chunks, the most "
            "relevant lines are shown below. The baseline retrieves better "
            "than keyword search but still does not reconcile conflicting "
            "evidence.\n\n" + top_snippets
        ),
        assessment=(
            f"Generated by vector retrieval (embeddings: {embedder.name}) over "
            "chunked raw_sources/. No synthesis, no contradiction handling, "
            "no hypothesis tracking. Better retrieval, same architecture gap."
        ),
        classification="fact",
        confidence="Low",
        supporting_sources=sorted({m.source_path for m in matches}),
        evidence_items=[f"{m.source_path} (cos={m.score:.2f}): {m.snippet[:160]}"
                        for m in matches],
        fell_back_to_raw_sources=True,
    )
