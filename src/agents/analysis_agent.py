"""Analysis Agent — extracts structured insights from research output."""

from __future__ import annotations

import time
from typing import Any

from agents.base_agent import AgentError, BaseAgent
from models.task import Task


class AnalysisAgent(BaseAgent):
    """Synthesizes research findings into ranked insights and risk factors.

    Expects `task.input_data["research"]` to be populated by an upstream
    ResearchAgent. In production, this would invoke an LLM reasoning step.
    """

    def __init__(self, simulate_delay: float = 0.1) -> None:
        super().__init__("AnalysisAgent")
        self._simulate_delay = simulate_delay

    def execute(self, task: Task) -> dict[str, Any]:
        self._log_start(task)
        research = task.input_data.get("research")
        if not research:
            raise AgentError("AnalysisAgent requires 'research' in task.input_data")
        try:
            analysis = self._analyze(research)
            self._log_complete(task)
            return {"analysis": analysis}
        except AgentError:
            raise
        except Exception as exc:
            self.logger.error(
                "Analysis step failed",
                extra={"task_id": task.id, "error": str(exc)},
            )
            raise AgentError(f"AnalysisAgent failed: {exc}") from exc

    def _analyze(self, research: dict[str, Any]) -> dict[str, Any]:
        time.sleep(self._simulate_delay)
        findings = research.get("findings", [])
        high_relevance = [f for f in findings if f.get("relevance_score", 0) >= 0.90]

        return {
            "goal": research.get("goal"),
            "findings_analyzed": len(findings),
            "key_themes": [
                "Generative AI market growth at 37%+ CAGR",
                "Agentic and multi-model orchestration as critical infrastructure",
                "Enterprise adoption accelerating with faster ROI realization",
                "Multi-modal models narrowing gap with specialist systems",
            ],
            "strategic_insights": [
                {
                    "insight": "Agent orchestration is becoming the dominant architecture pattern",
                    "confidence": 0.93,
                    "supporting_sources": [f["source"] for f in high_relevance],
                },
                {
                    "insight": (
                        "Enterprise ROI timelines have compressed 3x — "
                        "barriers to AI adoption are falling rapidly"
                    ),
                    "confidence": 0.89,
                    "supporting_sources": ["market_databases"],
                },
                {
                    "insight": (
                        "Emergent multi-modal capabilities will commoditize "
                        "single-modality specialist models within 24 months"
                    ),
                    "confidence": 0.82,
                    "supporting_sources": ["academic_papers"],
                },
            ],
            "risk_factors": [
                "Regulatory uncertainty around AI governance and liability",
                "Model commoditization compressing AI vendor margins",
                "Talent scarcity in AI systems and infrastructure engineering",
            ],
            "data_quality_score": research.get("data_quality_score", 0.0),
            "analysis_confidence": 0.88,
        }
