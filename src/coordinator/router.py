"""Task-to-agent routing with a registry-based dispatch table."""

from __future__ import annotations

from agents.analysis_agent import AnalysisAgent
from agents.base_agent import BaseAgent
from agents.reporting_agent import ReportingAgent
from agents.research_agent import ResearchAgent
from models.task import Task, TaskType
from utils.logging_utils import get_logger


class RoutingError(Exception):
    """Raised when no agent is registered for a given TaskType."""


class Router:
    """Maps TaskType values to their responsible agent instances.

    Designed for dependency injection: pass a custom registry to override
    individual agents (e.g., inject mocks during testing or swap
    implementations without modifying the coordinator).

    Example::

        router = Router({
            TaskType.RESEARCH: ResearchAgent(sources=["internal_db"]),
            TaskType.ANALYSIS: AnalysisAgent(),
            TaskType.REPORT:   ReportingAgent(),
        })
    """

    def __init__(self, agent_registry: dict[TaskType, BaseAgent] | None = None) -> None:
        self._registry: dict[TaskType, BaseAgent] = (
            agent_registry if agent_registry is not None else self._build_default_registry()
        )
        self._logger = get_logger("coordinator.router")

    @staticmethod
    def _build_default_registry() -> dict[TaskType, BaseAgent]:
        return {
            TaskType.RESEARCH: ResearchAgent(),
            TaskType.ANALYSIS: AnalysisAgent(),
            TaskType.REPORT:   ReportingAgent(),
        }

    def route(self, task: Task) -> BaseAgent:
        """Return the agent responsible for this task type.

        Raises:
            RoutingError: if no agent is registered for the task's type.
        """
        agent = self._registry.get(task.type)
        if agent is None:
            raise RoutingError(f"No agent registered for task type: {task.type!r}")
        self._logger.info(
            "Task routed",
            extra={"task_id": task.id, "task_type": task.type, "agent": agent.name},
        )
        return agent

    def register(self, task_type: TaskType, agent: BaseAgent) -> None:
        """Register or replace an agent for the given task type."""
        self._registry[task_type] = agent
        self._logger.info(
            "Agent registered",
            extra={"task_type": task_type, "agent": agent.name},
        )

    @property
    def registered_types(self) -> list[TaskType]:
        return list(self._registry.keys())
