"""Vector-RAG baseline: hashing embedder, retrieval, and benchmark wiring.

All tests use the deterministic ``hash`` backend so they run without
sentence-transformers and produce identical results everywhere.
"""
from __future__ import annotations

from pathlib import Path

from src.vector_rag import (
    HashingEmbedder,
    build_chunks,
    get_embedder,
    vector_rag_query,
    vector_search,
)

CASE = "case_001"


# --------------------------------------------------------------------------- #
# Hashing embedder
# --------------------------------------------------------------------------- #


def test_hash_embedder_is_deterministic() -> None:
    e = HashingEmbedder()
    a1 = e.embed(["powershell launched an unknown binary"])[0]
    a2 = e.embed(["powershell launched an unknown binary"])[0]
    assert a1 == a2


def test_hash_embedder_vectors_are_normalised() -> None:
    e = HashingEmbedder()
    vec = e.embed(["registry run key persistence"])[0]
    norm = sum(v * v for v in vec) ** 0.5
    assert abs(norm - 1.0) < 1e-9


def test_hash_embedder_ranks_related_text_higher() -> None:
    e = HashingEmbedder()
    query, related, unrelated = e.embed([
        "was malware confirmed by the antivirus scan",
        "windows defender full scan found no malware threats",
        "the quarterly sales figures rose in march",
    ])
    dot = lambda a, b: sum(x * y for x, y in zip(a, b, strict=True))  # noqa: E731
    assert dot(query, related) > dot(query, unrelated)


def test_get_embedder_defaults_to_hash(monkeypatch) -> None:
    monkeypatch.delenv("FORENSIC_WIKI_EMBEDDINGS", raising=False)
    assert isinstance(get_embedder(), HashingEmbedder)


# --------------------------------------------------------------------------- #
# Chunking and retrieval
# --------------------------------------------------------------------------- #


def test_build_chunks_covers_all_sources(project: Path) -> None:
    chunks = build_chunks(project, CASE)
    assert chunks
    sources = {c.source_path for c in chunks}
    assert any("defender_scan" in s for s in sources)
    assert any("investigator_notes" in s for s in sources)
    for c in chunks:
        assert c.text.strip()
        assert c.source_path.startswith("raw_sources/")


def test_vector_search_returns_ranked_matches(project: Path) -> None:
    matches = vector_search(project, CASE, "Is this confirmed malware?")
    assert matches
    scores = [m.score for m in matches]
    assert scores == sorted(scores, reverse=True)
    assert all(m.snippet for m in matches)


def test_vector_search_empty_case_returns_nothing(project: Path) -> None:
    assert vector_search(project, "case_does_not_exist", "anything") == []


# --------------------------------------------------------------------------- #
# vector_rag_query answer shape
# --------------------------------------------------------------------------- #


def test_vector_query_answers_with_sources(project: Path) -> None:
    ans = vector_rag_query(project, CASE, "Is this confirmed malware?")
    assert ans.insufficient is False
    assert ans.fell_back_to_raw_sources is True
    assert ans.supporting_sources
    assert all(s.startswith("raw_sources/") for s in ans.supporting_sources)
    assert "embedding" in ans.answer.lower() or "similarity" in ans.answer.lower()
    # The architecture gap is stated, not hidden.
    assert "no contradiction handling" in ans.assessment.lower()


def test_vector_query_insufficient_when_no_sources(project: Path) -> None:
    ans = vector_rag_query(project, "case_does_not_exist", "anything")
    assert ans.insufficient is True


def test_vector_query_does_not_synthesise_confirmation(project: Path) -> None:
    """Like raw RAG, the vector baseline must not manufacture a verdict —
    it returns snippets, so the words 'confirmed malware' may only appear
    if a raw source line says them."""
    ans = vector_rag_query(project, CASE, "Is this confirmed malware?")
    # case_001 raw sources never assert confirmed malware.
    assert "confirmed malware" not in ans.answer.lower()


# --------------------------------------------------------------------------- #
# Benchmark wiring
# --------------------------------------------------------------------------- #


def test_benchmark_methods_includes_vector_rag(project: Path) -> None:
    from src.benchmark_methods import METHODS, benchmark_methods, format_method_markdown
    from src.evolve import evolve_case
    from src.graph import build_graph, save_graph

    assert "vector_rag" in METHODS
    evolve_case(project, "case_002_evolving")
    save_graph(project, build_graph(project, "case_002_evolving"))
    summary = benchmark_methods(project, "case_002_evolving")
    assert "vector_rag" in summary.per_method
    for row in summary.rows:
        assert "vector_rag" in row.results
    md = format_method_markdown(summary)
    assert "Vector RAG" in md
