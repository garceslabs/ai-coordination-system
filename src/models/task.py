"""Core data models: Task, WorkflowState, and WorkflowResult."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


class TaskType(str, Enum):
    RESEARCH = "research"
    ANALYSIS = "analysis"
    REPORT = "report"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class WorkflowStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"  # some tasks succeeded before terminal failure


@dataclass
class Task:
    id: str
    type: TaskType
    goal: str
    workflow_id: str
    status: TaskStatus = TaskStatus.PENDING
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] | None = None
    dependencies: list[str] = field(default_factory=list)  # upstream task IDs
    retries: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None

    @classmethod
    def create(
        cls,
        task_type: TaskType,
        goal: str,
        workflow_id: str,
        input_data: dict[str, Any] | None = None,
        dependencies: list[str] | None = None,
        max_retries: int = 3,
    ) -> Task:
        return cls(
            id=str(uuid.uuid4()),
            type=task_type,
            goal=goal,
            workflow_id=workflow_id,
            input_data=input_data or {},
            dependencies=dependencies or [],
            max_retries=max_retries,
        )

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class WorkflowState:
    id: str
    goal: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    task_ids: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    final_output: dict[str, Any] | None = None
    error: str | None = None

    @classmethod
    def create(cls, goal: str) -> WorkflowState:
        return cls(id=str(uuid.uuid4()), goal=goal)

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class WorkflowResult:
    workflow_id: str
    goal: str
    status: WorkflowStatus
    output: dict[str, Any] | None
    task_results: dict[str, Any]
    duration_seconds: float | None
    error: str | None = None
