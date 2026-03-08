"""
Compatibilité API OpenAI — /v1/chat/completions
Permet à Open WebUI de s'y connecter comme à n'importe quel backend OpenAI.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from cognitive_core.graph import cognitive_graph

openai_router = APIRouter(tags=["openai-compat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "cognitive"
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None


@openai_router.get("/models")
async def list_models() -> dict:
    """Retourne les modèles disponibles."""
    return {
        "object": "list",
        "data": [
            {"id": "cognitive", "object": "model", "created": int(time.time()), "owned_by": "local"},
            {"id": "mistral", "object": "model", "created": int(time.time()), "owned_by": "local"},
            {"id": "phi3:mini", "object": "model", "created": int(time.time()), "owned_by": "local"},
        ],
    }


@openai_router.post("/chat/completions")
async def chat_completions(req: ChatCompletionRequest) -> Any:
    """
    Endpoint compatible OpenAI.
    Extrait la dernière question utilisateur et la passe au graphe cognitif.
    """
    # Extraire la dernière question utilisateur
    user_messages = [m for m in req.messages if m.role == "user"]
    query = user_messages[-1].content if user_messages else ""

    session_id = str(uuid.uuid4())

    initial_state = {
        "query": query,
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

    result = await cognitive_graph.ainvoke(initial_state)
    answer = result.get("final_answer", "")

    if req.stream:
        return StreamingResponse(
            _stream_response(answer, session_id),
            media_type="text/event-stream",
        )

    return {
        "id": f"chatcmpl-{session_id}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": answer},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


async def _stream_response(content: str, session_id: str) -> AsyncGenerator[str, None]:
    """Simule un streaming chunk-by-chunk."""
    import json

    words = content.split(" ")
    for i, word in enumerate(words):
        chunk = {
            "id": f"chatcmpl-{session_id}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "cognitive",
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": word + (" " if i < len(words) - 1 else "")},
                    "finish_reason": None,
                }
            ],
        }
        yield f"data: {json.dumps(chunk)}\n\n"

    # Signal de fin
    yield "data: [DONE]\n\n"
