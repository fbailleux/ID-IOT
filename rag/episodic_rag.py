"""
Episodic RAG — Redis (court terme) + PostgreSQL (long terme)
Mémoire des expériences passées du système.

Cycle :
  incident → analyse → solution → stockage
  problème similaire → rappel de l'expérience passée

Chaque épisode = {query, answer, session_id, timestamp, embedding}
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import redis.asyncio as aioredis
from langchain_ollama import OllamaEmbeddings
import asyncpg

logger = logging.getLogger(__name__)

# TTL Redis : 24h pour la mémoire court terme
REDIS_TTL = 86400
SIMILARITY_THRESHOLD = 0.75


class EpisodicRAG:
    """Gestion de la mémoire épisodique (expériences passées)."""

    def __init__(self) -> None:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        postgres_url = os.getenv("POSTGRES_URL", "")
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")

        self._redis = aioredis.from_url(redis_url, decode_responses=True)
        self._postgres_url = postgres_url
        self._pg_pool: asyncpg.Pool | None = None
        self._embeddings = OllamaEmbeddings(
            base_url=ollama_url,
            model="nomic-embed-text",
        )

    async def _get_pg_pool(self) -> asyncpg.Pool:
        if self._pg_pool is None:
            self._pg_pool = await asyncpg.create_pool(self._postgres_url)
        return self._pg_pool

    # ── Stockage ────────────────────────────────────────────────────────────

    async def store(
        self,
        query: str,
        answer: str,
        session_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Stocke un épisode dans Redis (court terme) et PostgreSQL (long terme).
        """
        timestamp = time.time()
        embedding = await self._embeddings.aembed_query(query)

        episode = {
            "query": query,
            "answer": answer,
            "session_id": session_id,
            "timestamp": timestamp,
            "metadata": metadata or {},
            "embedding": embedding,
        }

        # Court terme — Redis
        redis_key = f"episode:{session_id}:{int(timestamp)}"
        await self._redis.setex(redis_key, REDIS_TTL, json.dumps(episode))
        logger.info(f"[EpisodicRAG] Épisode court terme : {redis_key}")

        # Long terme — PostgreSQL
        await self._pg_store(episode)

    async def _pg_store(self, episode: dict[str, Any]) -> None:
        try:
            pool = await self._get_pg_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO episodes (query, answer, session_id, timestamp, metadata, embedding)
                    VALUES ($1, $2, $3, to_timestamp($4), $5, $6)
                    """,
                    episode["query"],
                    episode["answer"],
                    episode["session_id"],
                    episode["timestamp"],
                    json.dumps(episode["metadata"]),
                    json.dumps(episode["embedding"]),
                )
        except Exception as e:
            logger.warning(f"[EpisodicRAG] Erreur stockage PG : {e}")

    # ── Rappel ──────────────────────────────────────────────────────────────

    async def recall(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        """
        Retrouve les épisodes passés similaires à la requête courante.
        Cherche d'abord dans Redis (récent), puis PostgreSQL (historique).
        """
        results: list[dict[str, Any]] = []
        query_embedding = await self._embeddings.aembed_query(query)

        # Redis — mémoire récente
        redis_results = await self._recall_from_redis(query_embedding, limit)
        results.extend(redis_results)

        # PostgreSQL — si besoin de plus de résultats
        if len(results) < limit:
            pg_results = await self._recall_from_pg(query_embedding, limit - len(results))
            results.extend(pg_results)

        return results[:limit]

    async def _recall_from_redis(
        self, query_embedding: list[float], limit: int
    ) -> list[dict[str, Any]]:
        try:
            keys = await self._redis.keys("episode:*")
            episodes = []
            for key in keys:
                raw = await self._redis.get(key)
                if raw:
                    ep = json.loads(raw)
                    score = _cosine_similarity(query_embedding, ep["embedding"])
                    if score >= SIMILARITY_THRESHOLD:
                        episodes.append({**ep, "score": score, "source": "redis"})

            episodes.sort(key=lambda x: x["score"], reverse=True)
            return episodes[:limit]
        except Exception as e:
            logger.warning(f"[EpisodicRAG] Erreur Redis recall : {e}")
            return []

    async def _recall_from_pg(
        self, query_embedding: list[float], limit: int
    ) -> list[dict[str, Any]]:
        try:
            pool = await self._get_pg_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT query, answer, session_id, timestamp, metadata, embedding
                    FROM episodes
                    ORDER BY timestamp DESC
                    LIMIT 50
                    """
                )
                episodes = []
                for row in rows:
                    ep_emb = json.loads(row["embedding"])
                    score = _cosine_similarity(query_embedding, ep_emb)
                    if score >= SIMILARITY_THRESHOLD:
                        episodes.append(
                            {
                                "query": row["query"],
                                "answer": row["answer"],
                                "session_id": row["session_id"],
                                "timestamp": str(row["timestamp"]),
                                "metadata": json.loads(row["metadata"]),
                                "score": score,
                                "source": "postgres",
                            }
                        )

                episodes.sort(key=lambda x: x["score"], reverse=True)
                return episodes[:limit]
        except Exception as e:
            logger.warning(f"[EpisodicRAG] Erreur PG recall : {e}")
            return []


# ── Utilitaire ──────────────────────────────────────────────────────────────
def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Similarité cosinus entre deux vecteurs."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x ** 2 for x in a) ** 0.5
    norm_b = sum(x ** 2 for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
