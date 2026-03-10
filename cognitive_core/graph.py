"""
LangGraph Cognitive Core
Workflow principal : Planner → RAG parallèle → Agent Swarm → Synthèse

Deux modes d'exécution RAG :
- Par défaut (USE_RAY=false) : fan-out LangGraph natif (4 nœuds async)
- Mode Ray (USE_RAY=true)   : nœud unique géré par Ray (distribué/local)
"""
from __future__ import annotations

import logging
import os
from typing import Any

from langgraph.graph import END, StateGraph

from cognitive_core.state import CognitiveState
from cognitive_core.nodes import (
    planner_node,
    vector_rag_node,
    graph_rag_node,
    document_rag_node,
    episodic_rag_node,
    ray_parallel_rag_node,
    agent_swarm_node,
    synthesis_node,
    episodic_store_node,
)

logger = logging.getLogger(__name__)

_USE_RAY = os.getenv("USE_RAY", "false").lower() == "true"


def build_cognitive_graph() -> Any:
    """
    Construit le graphe LangGraph du cerveau cognitif.

    Mode standard (USE_RAY=false) :
      planner → [vector_rag, graph_rag, document_rag, episodic_rag] (fan-out)
              → agent_swarm → synthesis → episodic_store → END

    Mode Ray (USE_RAY=true) :
      planner → parallel_rag (Ray) → agent_swarm → synthesis → episodic_store → END
    """
    graph = StateGraph(CognitiveState)

    # ── Nœuds communs ──────────────────────────────────────────────────────
    graph.add_node("planner", planner_node)
    graph.add_node("agent_swarm", agent_swarm_node)
    graph.add_node("synthesis", synthesis_node)
    graph.add_node("episodic_store", episodic_store_node)

    graph.set_entry_point("planner")

    if _USE_RAY:
        # ── Mode Ray : un seul nœud orchestre les 4 RAG en distribué ───────
        graph.add_node("parallel_rag", ray_parallel_rag_node)
        graph.add_edge("planner", "parallel_rag")
        graph.add_edge("parallel_rag", "agent_swarm")
        logger.info("[CognitiveGraph] Mode Ray activé (parallel_rag)")
    else:
        # ── Mode standard : fan-out LangGraph natif ─────────────────────────
        graph.add_node("vector_rag", vector_rag_node)
        graph.add_node("graph_rag", graph_rag_node)
        graph.add_node("document_rag", document_rag_node)
        graph.add_node("episodic_rag", episodic_rag_node)

        graph.add_edge("planner", "vector_rag")
        graph.add_edge("planner", "graph_rag")
        graph.add_edge("planner", "document_rag")
        graph.add_edge("planner", "episodic_rag")

        graph.add_edge("vector_rag", "agent_swarm")
        graph.add_edge("graph_rag", "agent_swarm")
        graph.add_edge("document_rag", "agent_swarm")
        graph.add_edge("episodic_rag", "agent_swarm")
        logger.info("[CognitiveGraph] Mode standard LangGraph fan-out")

    # ── Suite commune ───────────────────────────────────────────────────────
    graph.add_edge("agent_swarm", "synthesis")
    graph.add_edge("synthesis", "episodic_store")
    graph.add_edge("episodic_store", END)

    return graph.compile()


# Singleton compilé
cognitive_graph = build_cognitive_graph()
