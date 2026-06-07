"""Entry point — demonstrates a full coordination workflow end-to-end."""

import json
import sys

from coordinator.coordinator import Coordinator
from models.task import WorkflowStatus


def main(goal: str = "Analyze AI market trends and produce a strategic report") -> int:
    print(f"\nGoal: {goal}\n{'─' * 60}")

    coordinator = Coordinator()
    result = coordinator.run_workflow(goal)

    print(f"\nWorkflow ID : {result.workflow_id}")
    print(f"Status      : {result.status}")
    print(f"Duration    : {result.duration_seconds:.2f}s")

    if result.status is WorkflowStatus.COMPLETED and result.output:
        report = result.output.get("report", {})
        print(f"\n{'─' * 60}")
        print(f"Title: {report.get('title')}")
        print(f"\nExecutive Summary:\n{report.get('executive_summary')}")

        print("\nStrategic Recommendations:")
        for rec in report.get("strategic_recommendations", []):
            print(f"  {rec['priority']}. [{rec['confidence']:.0%}] {rec['recommendation']}")

        print("\nRisk Assessment:")
        for entry in report.get("risk_assessment", []):
            print(f"  - {entry['risk']}")

    if result.error:
        print(f"\nError: {result.error}", file=sys.stderr)

    print(f"\n{'─' * 60}")
    print("Task execution history:")
    for task in result.task_results.get("tasks", []):
        status_icon = "✓" if task["status"] == "COMPLETED" else "✗"
        retries = f" ({task['retries']} retries)" if task["retries"] else ""
        duration = f" [{task['duration_seconds']:.3f}s]" if task["duration_seconds"] else ""
        print(f"  {status_icon} {task['type']:<10}{duration}{retries}")

    return 0 if result.status is WorkflowStatus.COMPLETED else 1


if __name__ == "__main__":
    goal = " ".join(sys.argv[1:]) or "Analyze AI market trends and produce a strategic report"
    sys.exit(main(goal))
