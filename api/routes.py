"""
Routes de l'API Cognitive Core.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cognitive_core.graph import cognitive_graph

router = APIRouter(tags=["cognitive"])


class QueryRequest(BaseModel):
    query: str
    session_id: str | None = None


class IndexRequest(BaseModel):
    content: str
    metadata: dict[str, Any] | None = None
    rag_type: str = "vector"  # vector | document | graph


class QueryResponse(BaseModel):
    answer: str
    session_id: str
    plan: list[str]


@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest) -> QueryResponse:
    """Lance une requête complète dans le cerveau cognitif."""
    session_id = req.session_id or str(uuid.uuid4())

    initial_state = {
        "query": req.query,
        "session_id": session_id,
        "messages": [],
        "plan": [],
        "vector_results": [],
        "graph_results": [],
        "document_results": [],
        "episodic_results": [],
        "agent_output": "",
        "final_answer": "",
        "iteration": 0,
    }

    try:
        result = await cognitive_graph.ainvoke(initial_state)
        return QueryResponse(
            answer=result.get("final_answer", ""),
            session_id=session_id,
            plan=result.get("plan", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index")
async def index_document(req: IndexRequest) -> dict:
    """Indexe un document dans le RAG approprié."""
    from rag.vector_rag import VectorRAG
    from rag.document_rag import DocumentRAG

    if req.rag_type == "vector":
        rag = VectorRAG()
        count = await rag.index([{"content": req.content, "metadata": req.metadata or {}}])
        return {"indexed": count, "rag": "vector"}

    elif req.rag_type == "document":
        rag = DocumentRAG()
        doc_id = await rag.index_document(req.content, req.metadata)
        return {"document_id": doc_id, "rag": "document"}

    else:
        raise HTTPException(status_code=400, detail=f"rag_type inconnu : {req.rag_type}")


@router.get("/status")
async def status() -> dict:
    """État des services du système cognitif."""
    from rag.document_rag import DocumentRAG

    doc_rag = DocumentRAG()
    haystack_ok = await doc_rag.health()

    return {
        "cognitive_core": "ok",
        "haystack": "ok" if haystack_ok else "unreachable",
    }
