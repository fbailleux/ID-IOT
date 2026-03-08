"""
Définitions des agents CrewAI.
Chaque agent a un rôle, une expertise et des objectifs précis.
"""
from __future__ import annotations

from crewai import Agent
from langchain_core.language_models.chat_models import BaseChatModel


def make_planner_agent(llm: BaseChatModel) -> Agent:
    """Décompose les problèmes complexes en sous-tâches actionnables."""
    return Agent(
        role="Planner Agent",
        goal=(
            "Analyser la demande, identifier les dépendances entre tâches "
            "et produire un plan d'exécution optimal."
        ),
        backstory=(
            "Expert en décomposition de problèmes complexes. "
            "Tu transformes des objectifs flous en plans concrets et séquencés."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=True,
    )


def make_research_agent(llm: BaseChatModel) -> Agent:
    """Recherche et synthétise des informations depuis le contexte RAG."""
    return Agent(
        role="Research Agent",
        goal=(
            "Extraire les informations pertinentes du contexte fourni "
            "et identifier les lacunes de connaissance."
        ),
        backstory=(
            "Chercheur rigoureux spécialisé dans l'analyse d'informations hétérogènes. "
            "Tu sais distinguer le signal du bruit et citer tes sources."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def make_infra_agent(llm: BaseChatModel) -> Agent:
    """Analyse les aspects infrastructure : Docker, services, réseau."""
    return Agent(
        role="Infrastructure Agent",
        goal=(
            "Diagnostiquer l'état des services, conteneurs et configurations réseau. "
            "Proposer des actions correctives précises."
        ),
        backstory=(
            "Ingénieur DevOps senior avec 10 ans d'expérience sur Docker, Kubernetes et Linux. "
            "Tu penses en termes de disponibilité, latence et résilience."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def make_log_agent(llm: BaseChatModel) -> Agent:
    """Analyse les logs système et applicatifs."""
    return Agent(
        role="Log Analysis Agent",
        goal=(
            "Analyser les journaux (journalctl, docker logs, app logs) "
            "pour identifier des patterns d'erreurs, anomalies ou dégradations."
        ),
        backstory=(
            "Expert en observabilité et analyse de logs. "
            "Tu détectes les root causes à partir de traces et corrélations temporelles."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def make_synthesis_agent(llm: BaseChatModel) -> Agent:
    """Fusionne et structure les résultats de tous les agents."""
    return Agent(
        role="Synthesis Agent",
        goal=(
            "Fusionner les analyses de tous les agents en une réponse cohérente, "
            "hiérarchisée et actionnaire pour l'utilisateur."
        ),
        backstory=(
            "Expert en communication technique. "
            "Tu transformes des analyses complexes en recommandations claires et priorisées."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
