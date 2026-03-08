"""
Tâches CrewAI assignées à chaque agent.
"""
from __future__ import annotations

from crewai import Task
from crewai import Agent


def make_research_task(research_agent: Agent, query: str, context: str) -> Task:
    return Task(
        description=(
            f"Recherche et synthèse d'information\n\n"
            f"Question : {query}\n\n"
            f"Contexte RAG disponible :\n{context}\n\n"
            "Extrait les informations pertinentes, identifie les contradictions "
            "et liste ce qui reste inconnu."
        ),
        expected_output=(
            "Synthèse structurée avec : informations clés, sources, "
            "points d'incertitude et recommandations de recherche complémentaire."
        ),
        agent=research_agent,
    )


def make_infra_task(infra_agent: Agent, query: str, context: str) -> Task:
    return Task(
        description=(
            f"Analyse infrastructure\n\n"
            f"Contexte : {query}\n\n"
            f"Informations disponibles :\n{context}\n\n"
            "Identifie les problèmes d'infrastructure, services en échec, "
            "saturations mémoire/CPU, et problèmes réseau."
        ),
        expected_output=(
            "Rapport d'état infrastructure avec : services KO, causes probables, "
            "actions correctives priorisées."
        ),
        agent=infra_agent,
    )


def make_log_task(log_agent: Agent, query: str, context: str) -> Task:
    return Task(
        description=(
            f"Analyse des journaux système\n\n"
            f"Contexte : {query}\n\n"
            f"Données de log disponibles :\n{context}\n\n"
            "Recherche des patterns d'erreurs, stacktraces, timeouts "
            "et anomalies temporelles dans les logs."
        ),
        expected_output=(
            "Rapport d'analyse logs avec : erreurs récurrentes, timeline des événements, "
            "root cause probable et métriques clés."
        ),
        agent=log_agent,
    )


def make_synthesis_task(
    synthesis_agent: Agent, query: str, context_tasks: list[Task]
) -> Task:
    return Task(
        description=(
            f"Synthèse finale\n\n"
            f"Question originale : {query}\n\n"
            "Fusionne les analyses de tous les agents et produis une réponse "
            "complète, structurée et prête à être présentée à l'utilisateur. "
            "Priorise les actions concrètes."
        ),
        expected_output=(
            "Réponse finale en français, structurée avec : "
            "résumé exécutif, analyse détaillée, actions recommandées (priorisées), "
            "et risques identifiés."
        ),
        agent=synthesis_agent,
        context=context_tasks,
    )
