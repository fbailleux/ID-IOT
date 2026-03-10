"""
Tâches Ray distribuées pour les 4 backends RAG.

Chaque fonction @ray.remote s'exécute dans un worker Ray isolé,
permettant une vraie parallélisation distribuée (multi-cœur ou multi-nœud).

Note : les workers Ray sont des processus séparés, donc on utilise
asyncio.run() pour exécuter les coroutines async des RAG.
"""
from __future__ import annotations

import asyncio

import ray


@ray.remote
def vector_rag_search(query: str, k: int = 5) -> list[dict]:
    """Recherche sémantique distribuée dans Qdrant."""
    from rag.vector_rag import VectorRAG
    return asyncio.run(VectorRAG().search(query, k=k))


@ray.remote
def graph_rag_search(query: str, depth: int = 2) -> list[dict]:
    """Raisonnement relationnel distribué dans Neo4j."""
    from rag.graph_rag import GraphRAG
    return asyncio.run(GraphRAG().search(query, depth=depth))


@ray.remote
def document_rag_search(query: str, top_k: int = 5) -> list[dict]:
    """Extraction de passages distribuée via Haystack."""
    from rag.document_rag import DocumentRAG
    return asyncio.run(DocumentRAG().search(query, top_k=top_k))


@ray.remote
def episodic_rag_search(query: str, limit: int = 3) -> list[dict]:
    """Rappel d'expériences passées distribué (Redis + PostgreSQL)."""
    from rag.episodic_rag import EpisodicRAG
    return asyncio.run(EpisodicRAG().recall(query, limit=limit))
