"""Tests for Router — task-type to agent dispatch."""

from unittest.mock import MagicMock

import pytest

from agents.base_agent import BaseAgent
from coordinator.router import Router, RoutingError
from models.task import Task, TaskType


def test_routes_research_to_research_agent(fast_router, research_task):
    agent = fast_router.route(research_task)
    assert agent.name == "ResearchAgent"


def test_routes_analysis_to_analysis_agent(fast_router, workflow_id):
    task = Task.create(TaskType.ANALYSIS, "goal", workflow_id)
    assert fast_router.route(task).name == "AnalysisAgent"


def test_routes_report_to_reporting_agent(fast_router, workflow_id):
    task = Task.create(TaskType.REPORT, "goal", workflow_id)
    assert fast_router.route(task).name == "ReportingAgent"


def test_raises_routing_error_for_unregistered_type():
    empty_router = Router({})
    task = Task.create(TaskType.RESEARCH, "goal", "wf-1")
    with pytest.raises(RoutingError, match="No agent registered"):
        empty_router.route(task)


def test_register_overrides_existing_agent(fast_router, workflow_id):
    mock_agent = MagicMock(spec=BaseAgent)
    mock_agent.name = "MockResearchAgent"
    fast_router.register(TaskType.RESEARCH, mock_agent)
    assert fast_router.route(Task.create(TaskType.RESEARCH, "g", workflow_id)).name == "MockResearchAgent"


def test_registered_types_includes_all_defaults(fast_router):
    types = fast_router.registered_types
    assert TaskType.RESEARCH in types
    assert TaskType.ANALYSIS in types
    assert TaskType.REPORT in types


def test_empty_registry_has_no_registered_types():
    assert Router({}).registered_types == []
