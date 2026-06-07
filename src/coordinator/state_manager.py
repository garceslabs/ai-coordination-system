"""Thread-safe state store for workflow and task lifecycle management."""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any

from models.task import Task, TaskStatus, WorkflowState, WorkflowStatus
from utils.logging_utils import get_logger


class StateError(Exception):
    """Raised on illegal state transitions or missing entity lookups."""


class StateManager:
    """In-memory, thread-safe store for workflow and task state.

    All mutations go through explicit transition methods that enforce valid
    state machine paths. Illegal transitions raise immediately rather than
    silently corrupting state.

    State machine — Tasks:
        PENDING → RUNNING → COMPLETED (terminal)
                          → FAILED    → PENDING  (retry reset)

    State machine — Workflows:
        PENDING → RUNNING → COMPLETED (terminal)
                          → FAILED    (terminal)
                          → PARTIAL   (terminal; some tasks succeeded)
    """

    _VALID_TASK_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
        TaskStatus.PENDING:   {TaskStatus.RUNNING},
        TaskStatus.RUNNING:   {TaskStatus.COMPLETED, TaskStatus.FAILED},
        TaskStatus.COMPLETED: set(),
        TaskStatus.FAILED:    {TaskStatus.PENDING},  # retry reset only
    }

    _VALID_WORKFLOW_TRANSITIONS: dict[WorkflowStatus, set[WorkflowStatus]] = {
        WorkflowStatus.PENDING:  {WorkflowStatus.RUNNING},
        WorkflowStatus.RUNNING:  {WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.PARTIAL},
        WorkflowStatus.COMPLETED: set(),
        WorkflowStatus.FAILED:    set(),
        WorkflowStatus.PARTIAL:   set(),
    }

    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowState] = {}
        self._tasks: dict[str, Task] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("coordinator.state_manager")

    # ------------------------------------------------------------------ #
    # Workflow operations
    # ------------------------------------------------------------------ #

    def create_workflow(self, workflow: WorkflowState) -> WorkflowState:
        with self._lock:
            self._workflows[workflow.id] = workflow
            self._logger.info("Workflow created", extra={"workflow_id": workflow.id})
            return workflow

    def get_workflow(self, workflow_id: str) -> WorkflowState:
        with self._lock:
            workflow = self._workflows.get(workflow_id)
            if workflow is None:
                raise StateError(f"Workflow not found: {workflow_id!r}")
            return workflow

    def transition_workflow(
        self,
        workflow_id: str,
        new_status: WorkflowStatus,
        *,
        final_output: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> WorkflowState:
        with self._lock:
            workflow = self.get_workflow(workflow_id)
            self._assert_valid_workflow_transition(workflow.status, new_status)

            workflow.status = new_status
            if new_status is WorkflowStatus.RUNNING and workflow.started_at is None:
                workflow.started_at = datetime.utcnow()
            if new_status in {WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.PARTIAL}:
                workflow.completed_at = datetime.utcnow()
            if final_output is not None:
                workflow.final_output = final_output
            if error is not None:
                workflow.error = error

            self._logger.info(
                "Workflow transitioned",
                extra={"workflow_id": workflow_id, "new_status": new_status},
            )
            return workflow

    # ------------------------------------------------------------------ #
    # Task operations
    # ------------------------------------------------------------------ #

    def register_task(self, task: Task) -> Task:
        with self._lock:
            self._tasks[task.id] = task
            workflow = self._workflows.get(task.workflow_id)
            if workflow and task.id not in workflow.task_ids:
                workflow.task_ids.append(task.id)
            self._logger.info(
                "Task registered",
                extra={
                    "task_id": task.id,
                    "task_type": task.type,
                    "workflow_id": task.workflow_id,
                },
            )
            return task

    def get_task(self, task_id: str) -> Task:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise StateError(f"Task not found: {task_id!r}")
            return task

    def transition_task(
        self,
        task_id: str,
        new_status: TaskStatus,
        *,
        output_data: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> Task:
        with self._lock:
            task = self.get_task(task_id)
            self._assert_valid_task_transition(task.status, new_status)

            task.status = new_status

            if new_status is TaskStatus.RUNNING:
                task.started_at = datetime.utcnow()

            if new_status in {TaskStatus.COMPLETED, TaskStatus.FAILED}:
                task.completed_at = datetime.utcnow()

            if new_status is TaskStatus.PENDING:
                # Retry reset: clear ephemeral fields and increment counter
                task.retries += 1
                task.started_at = None
                task.completed_at = None
                task.error = None

            if output_data is not None:
                task.output_data = output_data
            if error is not None:
                task.error = error

            self._logger.info(
                "Task transitioned",
                extra={"task_id": task_id, "new_status": new_status},
            )
            return task

    def get_workflow_tasks(self, workflow_id: str) -> list[Task]:
        with self._lock:
            workflow = self.get_workflow(workflow_id)
            return [self._tasks[tid] for tid in workflow.task_ids if tid in self._tasks]

    def get_execution_history(self, workflow_id: str) -> dict[str, Any]:
        with self._lock:
            workflow = self.get_workflow(workflow_id)
            tasks = self.get_workflow_tasks(workflow_id)
            return {
                "workflow_id": workflow_id,
                "goal": workflow.goal,
                "status": workflow.status,
                "duration_seconds": workflow.duration_seconds,
                "tasks": [
                    {
                        "id": t.id,
                        "type": t.type,
                        "status": t.status,
                        "retries": t.retries,
                        "duration_seconds": t.duration_seconds,
                        "error": t.error,
                    }
                    for t in tasks
                ],
            }

    # ------------------------------------------------------------------ #
    # Validation helpers
    # ------------------------------------------------------------------ #

    def _assert_valid_task_transition(self, current: TaskStatus, new: TaskStatus) -> None:
        allowed = self._VALID_TASK_TRANSITIONS.get(current, set())
        if new not in allowed:
            raise StateError(
                f"Invalid task transition: {current} → {new}. Allowed: {allowed or 'none (terminal)'}"
            )

    def _assert_valid_workflow_transition(self, current: WorkflowStatus, new: WorkflowStatus) -> None:
        allowed = self._VALID_WORKFLOW_TRANSITIONS.get(current, set())
        if new not in allowed:
            raise StateError(
                f"Invalid workflow transition: {current} → {new}. Allowed: {allowed or 'none (terminal)'}"
            )
