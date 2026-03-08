"""
FastAPI application — Point d'entrée du Cognitive Core.
"""
from __future__ import annotations

import logging
import os

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from api.openai_compat import openai_router

# ── Logging ────────────────────────────────────────────────────────────────
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level))
logger = structlog.get_logger()

# ── Application ────────────────────────────────────────────────────────────
app = FastAPI(
    title="Cognitive Core API",
    description="Multi-RAG cognitive system — LangGraph + CrewAI + 4 RAG",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.include_router(openai_router, prefix="/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "cognitive-core"}


@app.on_event("startup")
async def startup() -> None:
    logger.info("Cognitive Core démarré", log_level=log_level)
