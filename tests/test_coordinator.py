from coordination.coordinator import Coordinator, Task, TaskRisk, TaskStatus


def test_low_risk_task_is_routed_to_agent():
    coordinator = Coordinator()
    task = Task(id="task-1", description="Summarize document", task_type="summarization")

    decision = coordinator.route(task)

    assert decision.status == TaskStatus.ROUTED
    assert decision.destination == "summarization_agent"


def test_high_risk_task_is_escalated():
    coordinator = Coordinator()
    task = Task(
        id="task-2",
        description="Approve regulated content",
        task_type="approval",
        risk=TaskRisk.HIGH,
    )

    decision = coordinator.route(task)

    assert decision.status == TaskStatus.ESCALATED
    assert decision.destination == "human_review"
