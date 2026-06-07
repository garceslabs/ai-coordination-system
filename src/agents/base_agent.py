"""Abstract base class for all task-execution agents."""

from __future__ import annotations

import abc
from typing import Any

from models.task import Task
from utils.logging_utils import get_logger


class AgentError(Exception):
    """Raised when an agent cannot complete a task."""


class BaseAgent(abc.ABC):
    """Contract that every agent must fulfill.

    Subclasses implement `execute` and receive structured logging,
    task lifecycle hooks, and a consistent error surface automatically.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.logger = get_logger(f"agent.{name}")

    @abc.abstractmethod
    def execute(self, task: Task) -> dict[str, Any]:
        """Run the task and return its output payload.

        Raises:
            AgentError: on any unrecoverable failure.
        """

    def _log_start(self, task: Task) -> None:
        self.logger.info(
            "Agent starting task",
            extra={"agent": self.name, "task_id": task.id, "task_type": task.type},
        )

    def _log_complete(self, task: Task) -> None:
        self.logger.info(
            "Agent completed task",
            extra={"agent": self.name, "task_id": task.id, "task_type": task.type},
        )
