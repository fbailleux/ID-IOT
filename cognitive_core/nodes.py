"""
Nœuds du graphe LangGraph.
Chaque nœud reçoit et retourne un CognitiveState partiel.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_ollama import ChatOllama

from cognitive_core.state import CognitiveState
from rag.vector_rag import VectorRAG
from rag.graph_rag import GraphRAG
from rag.document_rag import DocumentRAG
from rag.episodic_rag import EpisodicRAG
from agents.crew import build_crew

logger = logging.getLogger(__name__)

# ── LLM (Ollama local) ─────────────────────────────────────────────────────
import os

_llm = ChatOllama(
    base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
    model=os.getenv("DEFAULT_MODEL", "mistral"),
    temperature=0.1,
)

_fast_llm = ChatOllama(
    base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
    model=os.getenv("FAST_MODEL", "phi3:mini"),
    temperature=0.0,
)

# ── Singletons RAG ─────────────────────────────────────────────────────────
_vector_rag = VectorRAG()
_graph_rag = GraphRAG()
_document_rag = DocumentRAG()
_episodic_rag = EpisodicRAG()


# ── Nœud : Planner ─────────────────────────────────────────────────────────
async def planner_node(state: CognitiveState) -> dict[str, Any]:
    """
    Décompose la requête en sous-tâches.
    Utilise le modèle rapide pour minimiser la latence.
    """
    query = state["query"]
    logger.info(f"[Planner] Query: {query[:100]}")

    prompt = (
        "Tu es un planificateur cognitif. "
        "Décompose la demande suivante en 2 à 5 sous-tâches concrètes, "
        "une par ligne, sans numérotation ni tirets.\n\n"
        f"Demande : {query}"
    )

    response = await _fast_llm.ainvoke(prompt)
    plan = [line.strip() for line in response.content.split("\n") if line.strip()]

    logger.info(f"[Planner] Plan: {plan}")
    return {
        "plan": plan,
        "session_id": state.get("session_id") or str(uuid.uuid4()),
        "iteration": state.get("iteration", 0) + 1,
        "messages": [HumanMessage(content=query)],
    }


# ── Nœud : Vector RAG ──────────────────────────────────────────────────────
async def vector_rag_node(state: CognitiveState) -> dict[str, Any]:
    """Recherche sémantique dans Qdrant."""
    results = await _vector_rag.search(state["query"], k=5)
    logger.info(f"[VectorRAG] {len(results)} résultats")
    return {"vector_results": results}


# ── Nœud : Graph RAG ───────────────────────────────────────────────────────
async def graph_rag_node(state: CognitiveState) -> dict[str, Any]:
    """Raisonnement relationnel dans Neo4j."""
    results = await _graph_rag.search(state["query"], depth=2)
    logger.info(f"[GraphRAG] {len(results)} relations")
    return {"graph_results": results}


# ── Nœud : Document RAG ────────────────────────────────────────────────────
async def document_rag_node(state: CognitiveState) -> dict[str, Any]:
    """Extraction de passages depuis Haystack."""
    results = await _document_rag.search(state["query"], top_k=5)
    logger.info(f"[DocumentRAG] {len(results)} passages")
    return {"document_results": results}


# ── Nœud : Episodic RAG ────────────────────────────────────────────────────
async def episodic_rag_node(state: CognitiveState) -> dict[str, Any]:
    """Récupère les expériences passées similaires."""
    results = await _episodic_rag.recall(state["query"], limit=3)
    logger.info(f"[EpisodicRAG] {len(results)} souvenirs")
    return {"episodic_results": results}


# ── Nœud : Agent Swarm (CrewAI) ────────────────────────────────────────────
async def agent_swarm_node(state: CognitiveState) -> dict[str, Any]:
    """
    Lance le swarm d'agents CrewAI avec le contexte RAG consolidé.
    """
    context = _build_rag_context(state)
    crew = build_crew(llm=_llm)

    result = await crew.kickoff_async(
        inputs={
            "query": state["query"],
            "plan": "\n".join(state.get("plan", [])),
            "context": context,
        }
    )
    logger.info("[AgentSwarm] Terminé")
    return {"agent_output": str(result)}


# ── Nœud : Synthèse ────────────────────────────────────────────────────────
async def synthesis_node(state: CognitiveState) -> dict[str, Any]:
    """Fusionne les résultats agents en une réponse finale cohérente."""
    prompt = (
        "Tu es un synthétiseur cognitif expert. "
        "À partir des éléments ci-dessous, rédige une réponse complète, "
        "structurée et précise à la question de l'utilisateur.\n\n"
        f"Question : {state['query']}\n\n"
        f"Analyse des agents :\n{state.get('agent_output', '')}\n\n"
        "Réponds en français, de façon claire et structurée."
    )

    response = await _llm.ainvoke(prompt)
    logger.info("[Synthesis] Réponse générée")
    return {
        "final_answer": response.content,
        "messages": [AIMessage(content=response.content)],
    }


# ── Nœud : Stockage épisodique ─────────────────────────────────────────────
async def episodic_store_node(state: CognitiveState) -> dict[str, Any]:
    """Stocke l'épisode (question → réponse) pour apprentissage futur."""
    await _episodic_rag.store(
        query=state["query"],
        answer=state.get("final_answer", ""),
        session_id=state.get("session_id", ""),
        metadata={
            "plan": state.get("plan", []),
            "iteration": state.get("iteration", 0),
        },
    )
    logger.info("[EpisodicStore] Épisode sauvegardé")
    return {}


# ── Helpers ────────────────────────────────────────────────────────────────
def _build_rag_context(state: CognitiveState) -> str:
    """Consolide les 4 RAG en un bloc de contexte lisible."""
    sections = []

    if state.get("vector_results"):
        items = "\n".join(f"  - {r.get('content', '')[:200]}" for r in state["vector_results"])
        sections.append(f"[Vector RAG]\n{items}")

    if state.get("graph_results"):
        items = "\n".join(f"  - {r.get('relation', '')}" for r in state["graph_results"])
        sections.append(f"[Graph RAG]\n{items}")

    if state.get("document_results"):
        items = "\n".join(f"  - {r.get('content', '')[:200]}" for r in state["document_results"])
        sections.append(f"[Document RAG]\n{items}")

    if state.get("episodic_results"):
        items = "\n".join(
            f"  - Q: {r.get('query', '')} → A: {r.get('answer', '')[:150]}"
            for r in state["episodic_results"]
        )
        sections.append(f"[Episodic RAG]\n{items}")

    return "\n\n".join(sections) if sections else "Aucun contexte RAG disponible."
