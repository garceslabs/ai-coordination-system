"""Tests for Coordinator — end-to-end workflow orchestration and failure handling."""

from unittest.mock import MagicMock

import pytest

from agents.base_agent import AgentError
from agents.research_agent import ResearchAgent
from coordinator.coordinator import Coordinator
from coordinator.router import Router
from coordinator.state_manager import StateManager
from coordinator.task_queue import TaskQueue
from models.task import TaskType, WorkflowStatus


def _make_analysis_mock():
    m = MagicMock()
    m.name = "AnalysisAgent"
    m.execute.return_value = {
        "analysis": {
            "findings_analyzed": 1, "key_themes": [], "strategic_insights": [],
            "risk_factors": [], "analysis_confidence": 0.9, "data_quality_score": 0.9,
        }
    }
    return m


def _make_report_mock():
    m = MagicMock()
    m.name = "ReportingAgent"
    m.execute.return_value = {"report": {"title": "Test Report"}}
    return m


def _fast_coordinator(**overrides) -> Coordinator:
    """Build a coordinator with fast agents and no retry sleep."""
    defaults = dict(
        router=Router({
            TaskType.RESEARCH: ResearchAgent(simulate_delay=0),
            TaskType.ANALYSIS: _make_analysis_mock(),
            TaskType.REPORT:   _make_report_mock(),
        }),
        state_manager=StateManager(),
        task_queue=TaskQueue(),
        retry_base_delay=0,
    )
    defaults.update(overrides)
    return Coordinator(**defaults)


# ------------------------------------------------------------------ #
# Happy path
# ------------------------------------------------------------------ #

def test_successful_workflow_status_is_completed(coordinator):
    result = coordinator.run_workflow("Analyze AI market trends")
    assert result.status is WorkflowStatus.COMPLETED


def test_successful_workflow_output_contains_all_pipeline_keys(coordinator):
    result = coordinator.run_workflow("Analyze AI market trends")
    assert "research" in result.output
    assert "analysis" in result.output
    assert "report" in result.output


def test_workflow_duration_is_non_negative(coordinator):
    result = coordinator.run_workflow("Analyze AI market trends")
    assert result.duration_seconds is not None
    assert result.duration_seconds >= 0


def test_task_results_history_contains_three_tasks(coordinator):
    result = coordinator.run_workflow("Analyze AI market trends")
    assert len(result.task_results["tasks"]) == 3


def test_task_results_include_all_task_types(coordinator):
    result = coordinator.run_workflow("Analyze AI market trends")
    types = {t["type"] for t in result.task_results["tasks"]}
    assert "research" in types
    assert "analysis" in types
    assert "report" in types


def test_get_workflow_status_returns_history(coordinator):
    result = coordinator.run_workflow("history test")
    history = coordinator.get_workflow_status(result.workflow_id)
    assert history["workflow_id"] == result.workflow_id
    assert len(history["tasks"]) == 3


# ------------------------------------------------------------------ #
# Retry behaviour
# ------------------------------------------------------------------ #

def test_transient_failure_triggers_retry_and_succeeds():
    call_count = 0
    real_agent = ResearchAgent(simulate_delay=0)

    def flaky_execute(task):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise AgentError("transient network error")
        return real_agent.execute(task)

    flaky = MagicMock()
    flaky.name = "FlakyResearch"
    flaky.execute.side_effect = flaky_execute

    coord = _fast_coordinator()
    coord._router.register(TaskType.RESEARCH, flaky)
    result = coord.run_workflow("retry test")

    assert call_count == 2
    assert result.status is WorkflowStatus.COMPLETED


def test_max_retries_exhausted_marks_workflow_failed():
    failing_agent = MagicMock()
    failing_agent.name = "AlwaysFails"
    failing_agent.execute.side_effect = AgentError("permanent failure")

    coord = Coordinator(
        router=Router({
            TaskType.RESEARCH: failing_agent,
            TaskType.ANALYSIS: MagicMock(name="unused"),
            TaskType.REPORT:   MagicMock(name="unused"),
        }),
        state_manager=StateManager(),
        task_queue=TaskQueue(),
        retry_base_delay=0,
    )
    result = coord.run_workflow("failing goal")
    assert result.status is WorkflowStatus.FAILED
    assert result.error is not None


def test_retry_count_is_recorded_in_task_history():
    failing_agent = MagicMock()
    failing_agent.name = "AlwaysFails"
    failing_agent.execute.side_effect = AgentError("err")

    coord = Coordinator(
        router=Router({
            TaskType.RESEARCH: failing_agent,
            TaskType.ANALYSIS: MagicMock(name="unused"),
            TaskType.REPORT:   MagicMock(name="unused"),
        }),
        state_manager=StateManager(),
        task_queue=TaskQueue(),
        retry_base_delay=0,
    )
    result = coord.run_workflow("retry count test")
    research_task = next(
        t for t in result.task_results["tasks"] if t["type"] == "research"
    )
    # max_retries=3 → 3 retry resets → retries==3
    assert research_task["retries"] == 3


# ------------------------------------------------------------------ #
# Partial completion
# ------------------------------------------------------------------ #

def test_partial_status_when_second_stage_fails():
    failing_analysis = MagicMock()
    failing_analysis.name = "FailingAnalysis"
    failing_analysis.execute.side_effect = AgentError("analysis crashed")

    coord = Coordinator(
        router=Router({
            TaskType.RESEARCH: ResearchAgent(simulate_delay=0),
            TaskType.ANALYSIS: failing_analysis,
            TaskType.REPORT:   MagicMock(name="unused"),
        }),
        state_manager=StateManager(),
        task_queue=TaskQueue(),
        retry_base_delay=0,
    )
    result = coord.run_workflow("partial test")
    assert result.status is WorkflowStatus.PARTIAL
    assert "research" in result.output


def test_failed_status_when_first_stage_fails_with_no_output():
    failing_research = MagicMock()
    failing_research.name = "FailingResearch"
    failing_research.execute.side_effect = AgentError("no data")

    coord = Coordinator(
        router=Router({
            TaskType.RESEARCH: failing_research,
            TaskType.ANALYSIS: MagicMock(name="unused"),
            TaskType.REPORT:   MagicMock(name="unused"),
        }),
        state_manager=StateManager(),
        task_queue=TaskQueue(),
        retry_base_delay=0,
    )
    result = coord.run_workflow("empty pipeline test")
    assert result.status is WorkflowStatus.FAILED
