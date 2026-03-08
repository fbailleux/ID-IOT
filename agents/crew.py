"""
Swarm d'agents CrewAI.
Construit et coordonne les 5 agents spécialisés.
"""
from __future__ import annotations

import logging
from typing import Any

from crewai import Crew, Process
from langchain_core.language_models.chat_models import BaseChatModel

from agents.definitions import (
    make_planner_agent,
    make_research_agent,
    make_infra_agent,
    make_log_agent,
    make_synthesis_agent,
)
from agents.tasks import (
    make_research_task,
    make_infra_task,
    make_log_task,
    make_synthesis_task,
)

logger = logging.getLogger(__name__)


def build_crew(llm: BaseChatModel) -> Crew:
    """
    Construit le swarm CrewAI avec les 5 agents.
    Process.HIERARCHICAL : le planner coordonne les autres agents.
    """
    planner = make_planner_agent(llm)
    researcher = make_research_agent(llm)
    infra = make_infra_agent(llm)
    log_analyst = make_log_agent(llm)
    synthesizer = make_synthesis_agent(llm)

    crew = Crew(
        agents=[planner, researcher, infra, log_analyst, synthesizer],
        tasks=[],  # Tâches injectées au moment du kickoff
        process=Process.hierarchical,
        manager_agent=planner,
        verbose=False,
        memory=False,  # La mémoire est gérée par LangGraph / EpisodicRAG
    )

    return crew


def build_crew_with_tasks(llm: BaseChatModel, query: str, context: str) -> Crew:
    """
    Construit le swarm avec les tâches pré-configurées.
    Utile pour les appels synchrones.
    """
    researcher = make_research_agent(llm)
    infra = make_infra_agent(llm)
    log_analyst = make_log_agent(llm)
    synthesizer = make_synthesis_agent(llm)
    planner = make_planner_agent(llm)

    research_task = make_research_task(researcher, query, context)
    infra_task = make_infra_task(infra, query, context)
    log_task = make_log_task(log_analyst, query, context)
    final_task = make_synthesis_task(synthesizer, query, [research_task, infra_task, log_task])

    return Crew(
        agents=[planner, researcher, infra, log_analyst, synthesizer],
        tasks=[research_task, infra_task, log_task, final_task],
        process=Process.sequential,
        verbose=False,
        memory=False,
    )
