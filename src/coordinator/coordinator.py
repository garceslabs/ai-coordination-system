"""Core orchestration engine — plans, dispatches, retries, and aggregates."""

from __future__ import annotations

import time
from typing import Any

from agents.base_agent import AgentError
from coordinator.router import Router, RoutingError
from coordinator.state_manager import StateManager
from coordinator.task_queue import TaskQueue
from models.task import Task, TaskStatus, TaskType, WorkflowResult, WorkflowState, WorkflowStatus
from utils.logging_utils import get_logger


class Coordinator:
    """Orchestrates multi-agent workflows end-to-end from a single user goal.

    Responsibilities:
      - Planning:      decompose a goal into an ordered task DAG
      - Dispatching:   route each task to its registered agent via the Router
      - Fault recovery: retry failed tasks with exponential back-off
      - Observability: persist all state transitions through the StateManager

    All collaborators are injected, making the Coordinator fully testable
    without touching I/O, agents, or shared state.
    """

    _PIPELINE: tuple[TaskType, ...] = (
        TaskType.RESEARCH,
        TaskType.ANALYSIS,
        TaskType.REPORT,
    )
    _DEFAULT_RETRY_BASE_DELAY: float = 1.0  # seconds; doubles each attempt

    def __init__(
        self,
        router: Router | None = None,
        state_manager: StateManager | None = None,
        task_queue: TaskQueue | None = None,
        retry_base_delay: float = _DEFAULT_RETRY_BASE_DELAY,
    ) -> None:
        self._router = router or Router()
        self._state = state_manager or StateManager()
        self._queue = task_queue or TaskQueue()
        self._retry_base_delay = retry_base_delay
        self._logger = get_logger("coordinator")

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def run_workflow(self, goal: str) -> WorkflowResult:
        """Execute the full agent pipeline for a user-supplied goal.

        Returns a WorkflowResult regardless of success or failure, always
        with a populated task_results history for post-mortem analysis.
        """
        workflow = WorkflowState.create(goal)
        self._state.create_workflow(workflow)

        self._logger.info(
            "Workflow started",
            extra={"workflow_id": workflow.id, "goal": goal},
        )

        try:
            self._state.transition_workflow(workflow.id, WorkflowStatus.RUNNING)
            tasks = self._plan(goal, workflow.id)
            for task in tasks:
                self._state.register_task(task)
            self._queue.enqueue_batch(tasks)

            accumulated: dict[str, Any] = {}

            while not self._queue.is_empty:
                task = self._queue.dequeue()
                if task is None:
                    break

                # Merge all upstream outputs into this task's input
                task.input_data.update(accumulated)

                self._execute_with_retry(task)

                if task.status is TaskStatus.FAILED:
                    return self._handle_failure(workflow, accumulated, failed_task=task)

                if task.output_data:
                    accumulated.update(task.output_data)

            self._state.transition_workflow(
                workflow.id,
                WorkflowStatus.COMPLETED,
                final_output=accumulated,
            )
            self._logger.info(
                "Workflow completed",
                extra={"workflow_id": workflow.id},
            )
            return self._build_result(workflow.id, accumulated)

        except Exception as exc:
            self._logger.error(
                "Workflow terminated with unexpected error",
                extra={"workflow_id": workflow.id},
                exc_info=True,
            )
            self._state.transition_workflow(
                workflow.id, WorkflowStatus.FAILED, error=str(exc)
            )
            return self._build_result(workflow.id, {}, error=str(exc))

    def get_workflow_status(self, workflow_id: str) -> dict[str, Any]:
        """Return full execution history for an existing workflow."""
        return self._state.get_execution_history(workflow_id)

    # ------------------------------------------------------------------ #
    # Planning
    # ------------------------------------------------------------------ #

    def _plan(self, goal: str, workflow_id: str) -> list[Task]:
        """Build a linear task pipeline. Override to support branching DAGs."""
        tasks: list[Task] = []
        prev_id: str | None = None
        for task_type in self._PIPELINE:
            task = Task.create(
                task_type=task_type,
                goal=goal,
                workflow_id=workflow_id,
                dependencies=[prev_id] if prev_id else [],
            )
            tasks.append(task)
            prev_id = task.id

        self._logger.info(
            "Execution plan created",
            extra={"workflow_id": workflow_id, "task_count": len(tasks)},
        )
        return tasks

    # ------------------------------------------------------------------ #
    # Execution with retry
    # ------------------------------------------------------------------ #

    def _execute_with_retry(self, task: Task) -> None:
        """Attempt task execution up to max_retries+1 times with exponential back-off.

        Mutates task.status and task.output_data so the caller can inspect
        the outcome without querying the state manager.
        """
        for attempt in range(task.max_retries + 1):
            try:
                self._state.transition_task(task.id, TaskStatus.RUNNING)
                agent = self._router.route(task)
                output = agent.execute(task)
                self._state.transition_task(task.id, TaskStatus.COMPLETED, output_data=output)
                task.status = TaskStatus.COMPLETED
                task.output_data = output
                return

            except (AgentError, RoutingError) as exc:
                is_final_attempt = attempt == task.max_retries
                self._logger.warning(
                    "Task attempt failed",
                    extra={
                        "task_id": task.id,
                        "task_type": task.type,
                        "attempt": attempt + 1,
                        "max_attempts": task.max_retries + 1,
                        "error": str(exc),
                    },
                )

                if is_final_attempt:
                    self._state.transition_task(task.id, TaskStatus.FAILED, error=str(exc))
                    task.status = TaskStatus.FAILED
                    return

                # Reset task state for the next attempt
                self._state.transition_task(task.id, TaskStatus.FAILED, error=str(exc))
                self._state.transition_task(task.id, TaskStatus.PENDING)

                delay = self._retry_base_delay * (2 ** attempt)
                self._logger.info(
                    "Scheduling retry",
                    extra={"task_id": task.id, "delay_seconds": delay, "attempt": attempt + 1},
                )
                time.sleep(delay)

    # ------------------------------------------------------------------ #
    # Result construction
    # ------------------------------------------------------------------ #

    def _handle_failure(
        self,
        workflow: WorkflowState,
        accumulated: dict[str, Any],
        *,
        failed_task: Task,
    ) -> WorkflowResult:
        error_msg = (
            f"Task {failed_task.id!r} ({failed_task.type}) "
            f"exhausted all retries: {failed_task.error}"
        )
        final_status = WorkflowStatus.PARTIAL if accumulated else WorkflowStatus.FAILED
        self._state.transition_workflow(workflow.id, final_status, error=error_msg)
        return self._build_result(workflow.id, accumulated, error=error_msg)

    def _build_result(
        self,
        workflow_id: str,
        output: dict[str, Any],
        error: str | None = None,
    ) -> WorkflowResult:
        workflow = self._state.get_workflow(workflow_id)
        return WorkflowResult(
            workflow_id=workflow_id,
            goal=workflow.goal,
            status=workflow.status,
            output=output or None,
            task_results=self._state.get_execution_history(workflow_id),
            duration_seconds=workflow.duration_seconds,
            error=error,
        )
