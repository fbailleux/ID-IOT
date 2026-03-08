"""
État partagé du graphe cognitif (LangGraph).
Chaque nœud lit/écrit dans ce TypedDict.
"""
from __future__ import annotations

from typing import Annotated, Any
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class CognitiveState(TypedDict):
    """État complet d'une session cognitive."""

    # Historique de conversation (accumulé via add_messages)
    messages: Annotated[list[BaseMessage], add_messages]

    # Question / tâche courante
    query: str

    # Plan décomposé par le Planner
    plan: list[str]

    # Résultats des 4 RAG
    vector_results: list[dict[str, Any]]
    graph_results: list[dict[str, Any]]
    document_results: list[dict[str, Any]]
    episodic_results: list[dict[str, Any]]

    # Résultats consolidés du swarm CrewAI
    agent_output: str

    # Réponse finale synthétisée
    final_answer: str

    # Méta-données de session
    session_id: str
    iteration: int
