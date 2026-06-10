"""GraphRAG-lite: a deliberately simple, file-based relationship graph.

The graph is **derived** from the structured indexes (events, entities,
claims) that ingest already produces. We never embed anything, we never
talk to Neo4j, and we never need a graph database — the data is small
enough that a JSON node/edge list is plenty.

The graph exists as a comparison foil:

  - Raw RAG     answers from raw snippets.
  - GraphRAG-lite answers from entity relationships.
  - LLM Wiki    answers from the compiled investigation state.
  - Hybrid      combines wiki + graph.

See ``docs/llm_wiki_vs_rag_vs_graphrag.md`` for the full positioning.
"""

from .graph_builder import build_graph, graph_md_path, graph_path, save_graph
from .graph_export import to_mermaid
from .graph_query import GraphAnswer, graph_query

__all__ = [
    "build_graph",
    "graph_md_path",
    "graph_path",
    "save_graph",
    "to_mermaid",
    "graph_query",
    "GraphAnswer",
]
