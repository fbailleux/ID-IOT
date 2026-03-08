"""
LangGraph Cognitive Core
Workflow principal : Planner → RAG parallèle → Agent Swarm → Synthèse
"""
from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from cognitive_core.state import CognitiveState
from cognitive_core.nodes import (
    planner_node,
    vector_rag_node,
    graph_rag_node,
    document_rag_node,
    episodic_rag_node,
    agent_swarm_node,
    synthesis_node,
    episodic_store_node,
)

logger = logging.getLogger(__name__)


def build_cognitive_graph() -> Any:
    """
    Construit le graphe LangGraph du cerveau cognitif.

    Flux :
    planner → [vector_rag, graph_rag, document_rag, episodic_rag] (parallèle)
            → agent_swarm → synthesis → episodic_store → END
    """
    graph = StateGraph(CognitiveState)

    # ── Nœuds ──────────────────────────────────────────────────────────────
    graph.add_node("planner", planner_node)
    graph.add_node("vector_rag", vector_rag_node)
    graph.add_node("graph_rag", graph_rag_node)
    graph.add_node("document_rag", document_rag_node)
    graph.add_node("episodic_rag", episodic_rag_node)
    graph.add_node("agent_swarm", agent_swarm_node)
    graph.add_node("synthesis", synthesis_node)
    graph.add_node("episodic_store", episodic_store_node)

    # ── Arêtes ─────────────────────────────────────────────────────────────
    graph.set_entry_point("planner")

    # Planner → 4 RAG en parallèle (fan-out)
    graph.add_edge("planner", "vector_rag")
    graph.add_edge("planner", "graph_rag")
    graph.add_edge("planner", "document_rag")
    graph.add_edge("planner", "episodic_rag")

    # 4 RAG → Agent Swarm (fan-in)
    graph.add_edge("vector_rag", "agent_swarm")
    graph.add_edge("graph_rag", "agent_swarm")
    graph.add_edge("document_rag", "agent_swarm")
    graph.add_edge("episodic_rag", "agent_swarm")

    # Agent Swarm → Synthèse → Stockage épisodique → FIN
    graph.add_edge("agent_swarm", "synthesis")
    graph.add_edge("synthesis", "episodic_store")
    graph.add_edge("episodic_store", END)

    return graph.compile()


# Singleton compilé
cognitive_graph = build_cognitive_graph()
