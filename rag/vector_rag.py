"""
Vector RAG — Qdrant
Recherche sémantique par similarité d'embeddings.
Retrouve : documents, conversations, notes similaires.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from langchain_ollama import OllamaEmbeddings
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

logger = logging.getLogger(__name__)

COLLECTION_NAME = "cognitive_memory"
VECTOR_SIZE = 768  # nomic-embed-text / mxbai-embed-large


class VectorRAG:
    """Recherche sémantique dans Qdrant."""

    def __init__(self) -> None:
        qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")

        self._client = AsyncQdrantClient(url=qdrant_url)
        self._embeddings = OllamaEmbeddings(
            base_url=ollama_url,
            model="nomic-embed-text",
        )

    async def ensure_collection(self) -> None:
        """Crée la collection si elle n'existe pas."""
        existing = await self._client.get_collections()
        names = [c.name for c in existing.collections]
        if COLLECTION_NAME not in names:
            await self._client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            logger.info(f"Collection '{COLLECTION_NAME}' créée dans Qdrant")

    async def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Recherche les k documents les plus similaires à la requête."""
        try:
            vector = await self._embeddings.aembed_query(query)
            results = await self._client.search(
                collection_name=COLLECTION_NAME,
                query_vector=vector,
                limit=k,
                with_payload=True,
            )
            return [
                {
                    "id": str(r.id),
                    "score": r.score,
                    "content": r.payload.get("content", "") if r.payload else "",
                    "metadata": r.payload.get("metadata", {}) if r.payload else {},
                }
                for r in results
            ]
        except Exception as e:
            logger.warning(f"[VectorRAG] Erreur recherche : {e}")
            return []

    async def index(self, documents: list[dict[str, Any]]) -> int:
        """
        Indexe une liste de documents dans Qdrant.
        Format attendu : [{"id": str, "content": str, "metadata": dict}]
        """
        await self.ensure_collection()

        vectors = await self._embeddings.aembed_documents(
            [doc["content"] for doc in documents]
        )

        points = [
            PointStruct(
                id=i,
                vector=vec,
                payload={"content": doc["content"], "metadata": doc.get("metadata", {})},
            )
            for i, (doc, vec) in enumerate(zip(documents, vectors))
        ]

        await self._client.upsert(collection_name=COLLECTION_NAME, points=points)
        logger.info(f"[VectorRAG] {len(points)} documents indexés")
        return len(points)
