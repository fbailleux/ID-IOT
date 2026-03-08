"""
Service Haystack — Document RAG
API FastAPI exposant les pipelines Haystack pour l'extraction de passages.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from haystack import Document, Pipeline
from haystack.components.embedders import (
    SentenceTransformersDocumentEmbedder,
    SentenceTransformersTextEmbedder,
)
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.document_stores.in_memory import InMemoryDocumentStore

logger = logging.getLogger(__name__)

app = FastAPI(title="Haystack Document RAG", version="1.0.0")

# ── Document Store (in-memory, persisté sur disque) ─────────────────────────
document_store = InMemoryDocumentStore()

# ── Pipeline de recherche ────────────────────────────────────────────────────
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

query_embedder = SentenceTransformersTextEmbedder(model=EMBED_MODEL)
retriever = InMemoryEmbeddingRetriever(document_store=document_store)

search_pipeline = Pipeline()
search_pipeline.add_component("query_embedder", query_embedder)
search_pipeline.add_component("retriever", retriever)
search_pipeline.connect("query_embedder.embedding", "retriever.query_embedding")

# ── Pipeline d'indexation ────────────────────────────────────────────────────
doc_embedder = SentenceTransformersDocumentEmbedder(model=EMBED_MODEL)
doc_embedder.warm_up()

index_pipeline = Pipeline()
index_pipeline.add_component("doc_embedder", doc_embedder)


# ── Modèles Pydantic ─────────────────────────────────────────────────────────
class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class IndexRequest(BaseModel):
    content: str
    metadata: dict[str, Any] | None = None


class SearchResult(BaseModel):
    content: str
    score: float
    metadata: dict[str, Any]


# ── Routes ───────────────────────────────────────────────────────────────────
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "documents": document_store.count_documents()}


@app.post("/search")
async def search(req: SearchRequest) -> dict:
    """Recherche les passages les plus pertinents."""
    try:
        result = search_pipeline.run(
            {"query_embedder": {"text": req.query}, "retriever": {"top_k": req.top_k}}
        )
        docs = result["retriever"]["documents"]
        return {
            "results": [
                {
                    "content": d.content,
                    "score": d.score or 0.0,
                    "metadata": d.meta or {},
                }
                for d in docs
            ]
        }
    except Exception as e:
        logger.error(f"Erreur recherche : {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/index")
async def index_document(req: IndexRequest) -> dict:
    """Indexe un document dans le store Haystack."""
    try:
        doc = Document(content=req.content, meta=req.metadata or {})
        result = index_pipeline.run({"doc_embedder": {"documents": [doc]}})
        embedded_docs = result["doc_embedder"]["documents"]
        document_store.write_documents(embedded_docs)
        return {"document_id": embedded_docs[0].id, "status": "indexed"}
    except Exception as e:
        logger.error(f"Erreur indexation : {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
