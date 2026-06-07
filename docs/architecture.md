# Architecture Reference

## Overview

The AI Coordination System is a layered, dependency-injected orchestration framework. Its design separates concerns across four distinct layers: data models, agent execution, coordination infrastructure, and observability.

---

## Layer Map

```
┌─────────────────────────────────────────────────────────┐
│                    Entry Point (main.py)                 │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│               Orchestration Layer                        │
│  Coordinator  ←→  StateManager                          │
│       ↕                                                  │
│  TaskQueue    ←→  Router                                │
└───────────────────────┬─────────────────────────────────┘
                        │ routes to
┌───────────────────────▼─────────────────────────────────┐
│                  Agent Layer                             │
│  BaseAgent (abstract)                                    │
│  ├── ResearchAgent                                       │
│  ├── AnalysisAgent                                       │
│  └── ReportingAgent                                      │
└───────────────────────┬─────────────────────────────────┘
                        │ uses
┌───────────────────────▼─────────────────────────────────┐
│              Data Model Layer (models/)                  │
│  Task  WorkflowState  WorkflowResult  Enums             │
└─────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

### Coordinator (`coordinator/coordinator.py`)

The single point of entry for all workflow operations. Owns the execution lifecycle:

1. Create a `WorkflowState` and register it with the StateManager
2. Call `_plan()` to produce an ordered list of `Task` objects
3. Enqueue the plan to the TaskQueue
4. Dequeue tasks one at a time, inject upstream outputs into `task.input_data`, and call `_execute_with_retry()`
5. On success, accumulate outputs; on failure, determine FAILED vs. PARTIAL outcome

The Coordinator is intentionally stateless between requests — all persistent state lives in the StateManager.

### Router (`coordinator/router.py`)

Registry pattern: a `dict[TaskType, BaseAgent]` that maps task types to agent instances. The registry is injected at construction, enabling full testability without any patching.

```python
router = Router({
    TaskType.RESEARCH: ResearchAgent(sources=["internal_rag"]),
    TaskType.ANALYSIS: AnalysisAgent(),
    TaskType.REPORT:   ReportingAgent(),
})
```

### StateManager (`coordinator/state_manager.py`)

A thread-safe in-memory store backed by two dictionaries and an `RLock`. All mutations go through typed transition methods that enforce the state machine:

- `transition_workflow(id, new_status)` — validates against `_VALID_WORKFLOW_TRANSITIONS`
- `transition_task(id, new_status)` — validates against `_VALID_TASK_TRANSITIONS`

Illegal transitions raise `StateError` immediately; they never silently corrupt state.

### TaskQueue (`coordinator/task_queue.py`)

A thin, thread-safe wrapper around `collections.deque`. Topology-aware ordering is the Coordinator/Planner's responsibility; the queue only manages FIFO dispatch. This separation means the queue can be swapped for a Redis-backed implementation without touching the Coordinator.

### BaseAgent (`agents/base_agent.py`)

Abstract base class that:
- Enforces the `execute(task) → dict` contract via `@abc.abstractmethod`
- Provides `_log_start` / `_log_complete` hooks so every agent gets structured logging without boilerplate
- Surfaces all failures as `AgentError` — a typed exception the Coordinator knows to catch and retry

---

## Data Model Design

### Task

```python
@dataclass
class Task:
    id: str                        # UUID
    type: TaskType                 # RESEARCH | ANALYSIS | REPORT
    goal: str                      # propagated from user input
    workflow_id: str               # parent workflow
    status: TaskStatus             # PENDING | RUNNING | COMPLETED | FAILED
    input_data: dict[str, Any]     # populated at dispatch time from upstream outputs
    output_data: dict[str, Any]    # written on COMPLETED
    dependencies: list[str]        # upstream task IDs (used by DAG planner)
    retries: int                   # number of retry resets (incremented by StateManager)
    max_retries: int               # configurable ceiling
    created_at / started_at / completed_at: datetime
    error: str | None
```

The `dependencies` field supports a future DAG planner — the Coordinator's `_plan()` method is the only place that needs to change.

### WorkflowState

Lightweight envelope grouping a list of task IDs with the workflow's own status and timing. The StateManager owns the authoritative list.

### WorkflowResult

Read-only output returned to the caller. Contains the aggregated output dict, the full execution history, duration, and any error message. Never mutated after construction.

---

## Dependency Injection Points

Every collaborator can be replaced at construction time:

```python
Coordinator(
    router=Router({TaskType.RESEARCH: MockResearchAgent()}),
    state_manager=StateManager(),         # swap: RedisStateManager()
    task_queue=TaskQueue(),               # swap: CeleryTaskQueue()
    retry_base_delay=0,                   # zero in tests
)
```

---

## Retry Protocol

```
attempt 0: PENDING → RUNNING → FAILED (error recorded)
                              ↓ not final attempt
             FAILED → PENDING (retries += 1, fields cleared)
attempt 1: PENDING → RUNNING → FAILED
                              ↓ not final attempt
             FAILED → PENDING
attempt 2: PENDING → RUNNING → FAILED (final)
           task.status = FAILED  (terminal)
```

Back-off: `delay = retry_base_delay × 2^attempt` (0s, 1s, 2s, 4s by default).

---

## Observability

Every significant event emits a structured JSON log:

```json
{
  "timestamp": "2025-06-06T14:23:01.456Z",
  "level": "INFO",
  "logger": "coordinator",
  "message": "Workflow started",
  "workflow_id": "a3f2c1d0-...",
  "goal": "Analyze AI market trends"
}
```

Fields are additive — each component attaches its own context (`task_id`, `agent`, `attempt`, `duration_seconds`). This makes logs queryable in any structured log aggregator (Datadog, CloudWatch, Loki).

---

## Extension Points

| Capability | Where to extend |
|-----------|----------------|
| New agent type | Add to `TaskType` enum, implement `BaseAgent`, register in `Router` |
| Parallel task execution | Override `Coordinator._plan()` to emit tasks with shared dependency IDs; add topological sort to executor |
| Persistent state | Implement `StateManager` interface against Redis / Postgres |
| LLM-backed agents | Inject an `anthropic.Anthropic` client into agent `__init__`; call in `_collect_research` / `_analyze` / `_generate_report` |
| Human-in-the-loop | Add `TaskType.REVIEW`, register a `HumanReviewAgent` that blocks on an external queue |
| Streaming progress | Publish events on each `transition_task` call via an event bus |
