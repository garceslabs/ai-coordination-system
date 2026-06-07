"""Shared pytest fixtures for the coordination system test suite."""

import pytest

from agents.analysis_agent import AnalysisAgent
from agents.reporting_agent import ReportingAgent
from agents.research_agent import ResearchAgent
from coordinator.coordinator import Coordinator
from coordinator.router import Router
from coordinator.state_manager import StateManager
from coordinator.task_queue import TaskQueue
from models.task import Task, TaskType, WorkflowState


@pytest.fixture
def state_manager() -> StateManager:
    return StateManager()


@pytest.fixture
def task_queue() -> TaskQueue:
    return TaskQueue()


@pytest.fixture
def fast_router() -> Router:
    """Router wired with zero-delay agents for test speed."""
    return Router({
        TaskType.RESEARCH: ResearchAgent(simulate_delay=0),
        TaskType.ANALYSIS: AnalysisAgent(simulate_delay=0),
        TaskType.REPORT:   ReportingAgent(simulate_delay=0),
    })


@pytest.fixture
def coordinator(fast_router, state_manager, task_queue) -> Coordinator:
    """Coordinator with fast agents and no retry delay."""
    return Coordinator(
        router=fast_router,
        state_manager=state_manager,
        task_queue=task_queue,
        retry_base_delay=0,
    )


@pytest.fixture
def workflow_id() -> str:
    return "test-workflow-abc"


@pytest.fixture
def research_task(workflow_id) -> Task:
    return Task.create(TaskType.RESEARCH, "Analyze AI market trends", workflow_id)


@pytest.fixture
def registered_workflow(state_manager, workflow_id) -> WorkflowState:
    wf = WorkflowState.create("test goal")
    wf.id = workflow_id
    state_manager.create_workflow(wf)
    return wf
