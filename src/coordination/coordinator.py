"""Core coordination engine."""

from dataclasses import dataclass
from enum import Enum


class TaskRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskStatus(str, Enum):
    ROUTED = "routed"
    ESCALATED = "escalated"


@dataclass(frozen=True)
class Task:
    id: str
    description: str
    task_type: str
    risk: TaskRisk = TaskRisk.LOW


@dataclass(frozen=True)
class RoutingDecision:
    task_id: str
    status: TaskStatus
    destination: str
    reason: str


class Coordinator:
    """Routes tasks to agents or human review based on risk and task type."""

    def route(self, task: Task) -> RoutingDecision:
        if task.risk == TaskRisk.HIGH:
            return RoutingDecision(
                task_id=task.id,
                status=TaskStatus.ESCALATED,
                destination="human_review",
                reason="High-risk task requires review before execution.",
            )

        destination = f"{task.task_type}_agent"
        return RoutingDecision(
            task_id=task.id,
            status=TaskStatus.ROUTED,
            destination=destination,
            reason="Task matched deterministic routing policy.",
        )
