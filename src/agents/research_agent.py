"""Research Agent — collects structured findings for a given goal."""

from __future__ import annotations

import time
from typing import Any

from agents.base_agent import AgentError, BaseAgent
from models.task import Task


class ResearchAgent(BaseAgent):
    """Queries configured sources and returns structured research findings.

    In production, `_collect_research` would call external APIs, RAG
    pipelines, or an LLM with tool use. The simulate_delay parameter
    controls artificial latency for integration testing.
    """

    DEFAULT_SOURCES: list[str] = [
        "industry_reports",
        "academic_papers",
        "market_databases",
        "news_aggregators",
    ]

    def __init__(
        self,
        sources: list[str] | None = None,
        simulate_delay: float = 0.1,
    ) -> None:
        super().__init__("ResearchAgent")
        self._sources = sources or self.DEFAULT_SOURCES
        self._simulate_delay = simulate_delay

    def execute(self, task: Task) -> dict[str, Any]:
        self._log_start(task)
        try:
            research = self._collect_research(task.goal)
            self._log_complete(task)
            return {"research": research}
        except Exception as exc:
            self.logger.error(
                "Research collection failed",
                extra={"task_id": task.id, "error": str(exc)},
            )
            raise AgentError(f"ResearchAgent failed: {exc}") from exc

    def _collect_research(self, goal: str) -> dict[str, Any]:
        time.sleep(self._simulate_delay)
        return {
            "goal": goal,
            "sources_queried": self._sources,
            "findings": [
                {
                    "source": "industry_reports",
                    "title": "AI Market Landscape 2024–2025",
                    "summary": (
                        "The global AI market is projected to grow at 37.3% CAGR. "
                        "Key drivers include generative AI adoption, enterprise automation, "
                        "and LLM integration across industry verticals."
                    ),
                    "relevance_score": 0.95,
                },
                {
                    "source": "academic_papers",
                    "title": "Scaling Laws and Emergent Capabilities in LLMs",
                    "summary": (
                        "Emergent capabilities appear at model-scale thresholds. "
                        "Multi-modal models are rapidly closing performance gaps with "
                        "single-modality specialist systems."
                    ),
                    "relevance_score": 0.88,
                },
                {
                    "source": "market_databases",
                    "title": "Enterprise AI Adoption Metrics Q4 2024",
                    "summary": (
                        "65% of Fortune 500 companies have deployed AI in production. "
                        "ROI realization time has dropped from 18 months to under 6 months "
                        "due to improved tooling and orchestration frameworks."
                    ),
                    "relevance_score": 0.91,
                },
                {
                    "source": "news_aggregators",
                    "title": "Agentic AI and Multi-Model Orchestration: 2025 Trends",
                    "summary": (
                        "Agent frameworks and coordination systems are the dominant architectural "
                        "trend. Model routing, tool use, and task decomposition are emerging as "
                        "critical infrastructure for AI-native applications."
                    ),
                    "relevance_score": 0.93,
                },
            ],
            "data_quality_score": 0.92,
        }
