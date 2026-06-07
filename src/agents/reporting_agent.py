"""Reporting Agent — generates the final structured report from analysis output."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from agents.base_agent import AgentError, BaseAgent
from models.task import Task


class ReportingAgent(BaseAgent):
    """Renders a structured strategic report from analysis insights.

    Expects `task.input_data["analysis"]` to be populated by an upstream
    AnalysisAgent. In production, this step would use an LLM to produce
    prose, export to PDF/Markdown, or push to an external system.
    """

    def __init__(self, simulate_delay: float = 0.1) -> None:
        super().__init__("ReportingAgent")
        self._simulate_delay = simulate_delay

    def execute(self, task: Task) -> dict[str, Any]:
        self._log_start(task)
        analysis = task.input_data.get("analysis")
        if not analysis:
            raise AgentError("ReportingAgent requires 'analysis' in task.input_data")
        try:
            report = self._generate_report(analysis, task.goal)
            self._log_complete(task)
            return {"report": report}
        except AgentError:
            raise
        except Exception as exc:
            self.logger.error(
                "Report generation failed",
                extra={"task_id": task.id, "error": str(exc)},
            )
            raise AgentError(f"ReportingAgent failed: {exc}") from exc

    def _generate_report(self, analysis: dict[str, Any], goal: str) -> dict[str, Any]:
        time.sleep(self._simulate_delay)
        themes = analysis.get("key_themes", [])
        insights = analysis.get("strategic_insights", [])
        risks = analysis.get("risk_factors", [])
        confidence = analysis.get("analysis_confidence", 0.0)
        n_findings = analysis.get("findings_analyzed", 0)

        return {
            "title": f"Strategic Report: {goal}",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "executive_summary": (
                f"This report analyzes {goal!r}. Drawing on {n_findings} data sources "
                f"with an aggregate confidence of {confidence:.0%}, the analysis surfaces "
                f"{len(insights)} strategic insights and {len(risks)} risk factors "
                f"across {len(themes)} key themes."
            ),
            "key_themes": themes,
            "strategic_recommendations": [
                {
                    "priority": idx + 1,
                    "recommendation": insight["insight"],
                    "confidence": insight["confidence"],
                    "action_items": [
                        "Benchmark current architecture against this trend",
                        "Identify internal capability gaps and quick wins",
                        "Define a 90-day proof-of-concept scope",
                    ],
                }
                for idx, insight in enumerate(insights)
            ],
            "risk_assessment": [
                {
                    "risk": risk,
                    "mitigation": (
                        "Monitor regulatory and competitive signals quarterly; "
                        "maintain architectural flexibility to adapt."
                    ),
                }
                for risk in risks
            ],
            "metadata": {
                "sources_analyzed": n_findings,
                "analysis_confidence": confidence,
                "data_quality_score": analysis.get("data_quality_score"),
            },
        }
