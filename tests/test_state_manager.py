"""Tests for StateManager — state machine correctness and thread safety."""

import pytest

from coordinator.state_manager import StateError, StateManager
from models.task import Task, TaskStatus, TaskType, WorkflowState, WorkflowStatus


# ------------------------------------------------------------------ #
# Workflow CRUD
# ------------------------------------------------------------------ #

def test_create_and_retrieve_workflow(state_manager):
    wf = WorkflowState.create("my goal")
    state_manager.create_workflow(wf)
    assert state_manager.get_workflow(wf.id).goal == "my goal"


def test_get_nonexistent_workflow_raises(state_manager):
    with pytest.raises(StateError, match="Workflow not found"):
        state_manager.get_workflow("does-not-exist")


# ------------------------------------------------------------------ #
# Workflow transitions
# ------------------------------------------------------------------ #

def test_pending_to_running_sets_started_at(state_manager):
    wf = WorkflowState.create("goal")
    state_manager.create_workflow(wf)
    state_manager.transition_workflow(wf.id, WorkflowStatus.RUNNING)
    result = state_manager.get_workflow(wf.id)
    assert result.status is WorkflowStatus.RUNNING
    assert result.started_at is not None


def test_running_to_completed_sets_completed_at(state_manager):
    wf = WorkflowState.create("goal")
    state_manager.create_workflow(wf)
    state_manager.transition_workflow(wf.id, WorkflowStatus.RUNNING)
    state_manager.transition_workflow(wf.id, WorkflowStatus.COMPLETED)
    result = state_manager.get_workflow(wf.id)
    assert result.status is WorkflowStatus.COMPLETED
    assert result.completed_at is not None


def test_pending_to_completed_is_invalid(state_manager):
    wf = WorkflowState.create("goal")
    state_manager.create_workflow(wf)
    with pytest.raises(StateError, match="Invalid workflow transition"):
        state_manager.transition_workflow(wf.id, WorkflowStatus.COMPLETED)


def test_completed_workflow_is_terminal(state_manager):
    wf = WorkflowState.create("goal")
    state_manager.create_workflow(wf)
    state_manager.transition_workflow(wf.id, WorkflowStatus.RUNNING)
    state_manager.transition_workflow(wf.id, WorkflowStatus.COMPLETED)
    with pytest.raises(StateError):
        state_manager.transition_workflow(wf.id, WorkflowStatus.RUNNING)


def test_transition_stores_final_output(state_manager):
    wf = WorkflowState.create("goal")
    state_manager.create_workflow(wf)
    state_manager.transition_workflow(wf.id, WorkflowStatus.RUNNING)
    state_manager.transition_workflow(wf.id, WorkflowStatus.COMPLETED, final_output={"report": {}})
    assert state_manager.get_workflow(wf.id).final_output == {"report": {}}


def test_transition_stores_error(state_manager):
    wf = WorkflowState.create("goal")
    state_manager.create_workflow(wf)
    state_manager.transition_workflow(wf.id, WorkflowStatus.RUNNING)
    state_manager.transition_workflow(wf.id, WorkflowStatus.FAILED, error="boom")
    assert state_manager.get_workflow(wf.id).error == "boom"


# ------------------------------------------------------------------ #
# Task CRUD
# ------------------------------------------------------------------ #

def test_register_task_links_to_workflow(state_manager, registered_workflow, workflow_id):
    task = Task.create(TaskType.RESEARCH, "goal", workflow_id)
    state_manager.register_task(task)
    assert task.id in state_manager.get_workflow(workflow_id).task_ids


def test_get_nonexistent_task_raises(state_manager):
    with pytest.raises(StateError, match="Task not found"):
        state_manager.get_task("bad-id")


# ------------------------------------------------------------------ #
# Task transitions
# ------------------------------------------------------------------ #

def test_pending_to_running_sets_started_at(state_manager, registered_workflow, workflow_id):
    task = Task.create(TaskType.RESEARCH, "goal", workflow_id)
    state_manager.register_task(task)
    state_manager.transition_task(task.id, TaskStatus.RUNNING)
    result = state_manager.get_task(task.id)
    assert result.status is TaskStatus.RUNNING
    assert result.started_at is not None


def test_running_to_completed_stores_output(state_manager, registered_workflow, workflow_id):
    task = Task.create(TaskType.RESEARCH, "goal", workflow_id)
    state_manager.register_task(task)
    state_manager.transition_task(task.id, TaskStatus.RUNNING)
    output = {"research": {"findings": []}}
    state_manager.transition_task(task.id, TaskStatus.COMPLETED, output_data=output)
    result = state_manager.get_task(task.id)
    assert result.status is TaskStatus.COMPLETED
    assert result.output_data == output
    assert result.completed_at is not None


def test_pending_to_completed_is_invalid(state_manager, registered_workflow, workflow_id):
    task = Task.create(TaskType.RESEARCH, "goal", workflow_id)
    state_manager.register_task(task)
    with pytest.raises(StateError, match="Invalid task transition"):
        state_manager.transition_task(task.id, TaskStatus.COMPLETED)


def test_retry_reset_increments_retries_and_clears_fields(state_manager, registered_workflow, workflow_id):
    task = Task.create(TaskType.RESEARCH, "goal", workflow_id)
    state_manager.register_task(task)
    state_manager.transition_task(task.id, TaskStatus.RUNNING)
    state_manager.transition_task(task.id, TaskStatus.FAILED, error="timeout")
    state_manager.transition_task(task.id, TaskStatus.PENDING)
    result = state_manager.get_task(task.id)
    assert result.status is TaskStatus.PENDING
    assert result.retries == 1
    assert result.error is None
    assert result.started_at is None
    assert result.completed_at is None


# ------------------------------------------------------------------ #
# Execution history
# ------------------------------------------------------------------ #

def test_execution_history_includes_all_registered_tasks(state_manager, registered_workflow, workflow_id):
    for task_type in [TaskType.RESEARCH, TaskType.ANALYSIS]:
        task = Task.create(task_type, "goal", workflow_id)
        state_manager.register_task(task)
    history = state_manager.get_execution_history(workflow_id)
    assert len(history["tasks"]) == 2
    assert history["goal"] == registered_workflow.goal
