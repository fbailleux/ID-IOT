"""
Document RAG — Haystack
Extraction de passages précis depuis des documents structurés.
Orchestré via l'API Haystack locale.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class DocumentRAG:
    """Client vers le service Haystack pour le RAG documentaire."""

    def __init__(self) -> None:
        self._base_url = os.getenv("HAYSTACK_URL", "http://haystack:8001")
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=30.0)

    async def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Recherche des passages pertinents dans les documents indexés."""
        try:
            response = await self._client.post(
                "/search",
                json={"query": query, "top_k": top_k},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            logger.warning(f"[DocumentRAG] Erreur recherche : {e}")
            return []

    async def index_document(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        """Indexe un document dans Haystack."""
        try:
            response = await self._client.post(
                "/index",
                json={"content": content, "metadata": metadata or {}},
            )
            response.raise_for_status()
            return response.json().get("document_id", "")
        except Exception as e:
            logger.warning(f"[DocumentRAG] Erreur indexation : {e}")
            return ""

    async def health(self) -> bool:
        """Vérifie que le service Haystack est disponible."""
        try:
            response = await self._client.get("/health")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()
