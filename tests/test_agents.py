"""Tests for individual agent execute() contracts and input validation."""

import pytest

from agents.analysis_agent import AnalysisAgent
from agents.base_agent import AgentError
from agents.reporting_agent import ReportingAgent
from agents.research_agent import ResearchAgent
from models.task import Task, TaskType


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture
def research_task():
    return Task.create(TaskType.RESEARCH, "Analyze AI market trends", "wf-agents")


@pytest.fixture
def research_output():
    return {
        "goal": "Analyze AI market trends",
        "sources_queried": ["industry_reports"],
        "findings": [
            {"source": "industry_reports", "title": "AI 2025", "summary": "Growth.", "relevance_score": 0.95},
        ],
        "data_quality_score": 0.9,
    }


@pytest.fixture
def analysis_task(research_output):
    return Task.create(
        TaskType.ANALYSIS,
        "Analyze AI market trends",
        "wf-agents",
        input_data={"research": research_output},
    )


@pytest.fixture
def analysis_output():
    return {
        "goal": "Analyze AI market trends",
        "findings_analyzed": 4,
        "key_themes": ["Generative AI growth", "Agentic orchestration"],
        "strategic_insights": [
            {"insight": "Orchestration is dominant pattern", "confidence": 0.93, "supporting_sources": ["industry_reports"]},
        ],
        "risk_factors": ["Regulatory uncertainty"],
        "data_quality_score": 0.92,
        "analysis_confidence": 0.88,
    }


@pytest.fixture
def report_task(analysis_output):
    return Task.create(
        TaskType.REPORT,
        "Analyze AI market trends",
        "wf-agents",
        input_data={"analysis": analysis_output},
    )


# ------------------------------------------------------------------ #
# ResearchAgent
# ------------------------------------------------------------------ #

class TestResearchAgent:
    def test_returns_research_key(self, research_task):
        result = ResearchAgent(simulate_delay=0).execute(research_task)
        assert "research" in result

    def test_findings_is_non_empty_list(self, research_task):
        result = ResearchAgent(simulate_delay=0).execute(research_task)
        assert isinstance(result["research"]["findings"], list)
        assert len(result["research"]["findings"]) > 0

    def test_data_quality_score_present(self, research_task):
        result = ResearchAgent(simulate_delay=0).execute(research_task)
        assert "data_quality_score" in result["research"]

    def test_sources_queried_matches_configured_sources(self, research_task):
        sources = ["source_a", "source_b"]
        result = ResearchAgent(sources=sources, simulate_delay=0).execute(research_task)
        assert result["research"]["sources_queried"] == sources

    def test_goal_is_echoed_in_output(self, research_task):
        result = ResearchAgent(simulate_delay=0).execute(research_task)
        assert result["research"]["goal"] == research_task.goal


# ------------------------------------------------------------------ #
# AnalysisAgent
# ------------------------------------------------------------------ #

class TestAnalysisAgent:
    def test_returns_analysis_key(self, analysis_task):
        result = AnalysisAgent(simulate_delay=0).execute(analysis_task)
        assert "analysis" in result

    def test_raises_when_research_missing(self):
        task = Task.create(TaskType.ANALYSIS, "goal", "wf-1")
        with pytest.raises(AgentError, match="requires 'research'"):
            AnalysisAgent(simulate_delay=0).execute(task)

    def test_key_themes_is_non_empty(self, analysis_task):
        result = AnalysisAgent(simulate_delay=0).execute(analysis_task)
        assert len(result["analysis"]["key_themes"]) > 0

    def test_strategic_insights_have_required_fields(self, analysis_task):
        result = AnalysisAgent(simulate_delay=0).execute(analysis_task)
        for insight in result["analysis"]["strategic_insights"]:
            assert "insight" in insight
            assert "confidence" in insight
            assert "supporting_sources" in insight

    def test_analysis_confidence_is_in_valid_range(self, analysis_task):
        result = AnalysisAgent(simulate_delay=0).execute(analysis_task)
        confidence = result["analysis"]["analysis_confidence"]
        assert 0.0 <= confidence <= 1.0


# ------------------------------------------------------------------ #
# ReportingAgent
# ------------------------------------------------------------------ #

class TestReportingAgent:
    def test_returns_report_key(self, report_task):
        result = ReportingAgent(simulate_delay=0).execute(report_task)
        assert "report" in result

    def test_raises_when_analysis_missing(self):
        task = Task.create(TaskType.REPORT, "goal", "wf-1")
        with pytest.raises(AgentError, match="requires 'analysis'"):
            ReportingAgent(simulate_delay=0).execute(task)

    def test_report_title_includes_goal(self, report_task):
        result = ReportingAgent(simulate_delay=0).execute(report_task)
        assert report_task.goal in result["report"]["title"]

    def test_executive_summary_is_present_and_non_empty(self, report_task):
        result = ReportingAgent(simulate_delay=0).execute(report_task)
        summary = result["report"]["executive_summary"]
        assert isinstance(summary, str) and len(summary) > 0

    def test_strategic_recommendations_are_prioritized(self, report_task):
        result = ReportingAgent(simulate_delay=0).execute(report_task)
        recs = result["report"]["strategic_recommendations"]
        priorities = [r["priority"] for r in recs]
        assert priorities == sorted(priorities)

    def test_risk_assessment_entries_have_mitigation(self, report_task):
        result = ReportingAgent(simulate_delay=0).execute(report_task)
        for risk_entry in result["report"]["risk_assessment"]:
            assert "risk" in risk_entry
            assert "mitigation" in risk_entry

    def test_metadata_contains_confidence_score(self, report_task):
        result = ReportingAgent(simulate_delay=0).execute(report_task)
        assert "analysis_confidence" in result["report"]["metadata"]
