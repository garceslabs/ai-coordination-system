# Design Decisions

Architecture decisions are recorded here with the context and trade-offs that drove each choice.

---

## ADR-001: Dependency Injection over Global State

**Decision:** All collaborators (Router, StateManager, TaskQueue) are injected into the Coordinator at construction time, with sensible defaults.

**Context:** AI coordination systems are hard to test because they interact with external APIs, shared state, and timing. A tightly coupled design forces `unittest.mock.patch` throughout the test suite, which is fragile and doesn't test real wiring.

**Consequences:**
- Core logic tests require no patching — pass a mock agent directly to the Router
- Swapping implementations (e.g., in-memory → Redis StateManager) requires no changes to the Coordinator
- Default construction (`Coordinator()`) still works for production use

---

## ADR-002: StateManager Enforces State Machine Transitions

**Decision:** Every task and workflow status change goes through a typed transition method that validates against an explicit allow-list. Illegal transitions raise immediately.

**Context:** In early prototypes, status fields were mutated directly. Silent invalid transitions (e.g., COMPLETED → RUNNING) caused subtle bugs that only appeared in failure scenarios.

**Consequences:**
- All state corruption is caught at the point of mutation, not at query time
- The state machine is self-documenting in `_VALID_TASK_TRANSITIONS` and `_VALID_WORKFLOW_TRANSITIONS`
- Adding a new status requires explicitly declaring its allowed predecessors and successors

---

## ADR-003: Linear Pipeline with DAG-Ready Interface

**Decision:** The current planner builds a linear Research → Analysis → Report pipeline. The `Task.dependencies` field and `Coordinator._plan()` method are designed to support a DAG without changes to the executor.

**Context:** Most real workflows start linear. Building a full DAG executor upfront adds complexity before the basic case is validated.

**Consequences:**
- First iteration is simpler to reason about and test
- Migrating to parallel branches requires only overriding `_plan()` and adding topological sort to the executor — no changes to Router, StateManager, or agents
- `dependencies` is present in the data model even though the linear executor doesn't use it for ordering (it uses queue position instead)

---

## ADR-004: Exponential Back-off Retry with Configurable Base Delay

**Decision:** `_execute_with_retry` retries up to `task.max_retries` times with a delay of `retry_base_delay × 2^attempt`. The base delay is a constructor argument defaulting to 1 second.

**Context:** Transient failures (network timeouts, rate limits, API flakiness) are common in LLM-backed systems. A fixed retry without back-off hammers a struggling service. Exponential back-off is the standard approach for retryable failures.

**Consequences:**
- Tests pass `retry_base_delay=0` to avoid slowing the suite
- Production callers can tune `max_retries` per task type in `Task.create()`
- The Coordinator distinguishes transient (`AgentError`, `RoutingError`) from unexpected (`Exception`) failures — only the former triggers retry

---

## ADR-005: PARTIAL Workflow Status

**Decision:** A workflow that completes some tasks before a terminal failure is marked `PARTIAL` rather than `FAILED`.

**Context:** When the AnalysisAgent fails after the ResearchAgent has already succeeded, the caller has partial, potentially useful output. Marking the whole workflow `FAILED` discards that signal. Operators want to know whether a workflow produced any output before failing.

**Consequences:**
- `WorkflowResult.output` can be non-null for a `PARTIAL` workflow
- Callers must check both `status` and `output` to determine what is usable
- `FAILED` is reserved for the case where no output was produced (first task failed immediately)

---

## ADR-006: Agents Receive Upstream Output via `task.input_data`

**Decision:** Before dispatching each task, the Coordinator merges all accumulated upstream outputs into `task.input_data`. Agents read from `task.input_data` rather than a separate context object.

**Context:** Alternatives considered:
1. Pass a shared context object alongside the task — adds a second parameter to `execute()`
2. Agent pulls output from StateManager by task ID — couples agents to infrastructure
3. Merge into `task.input_data` — agents remain infrastructure-agnostic

**Consequences:**
- `BaseAgent.execute(task)` signature stays simple and stable
- Agents can be tested in isolation by populating `task.input_data` directly
- `input_data` grows as the pipeline progresses (all upstream outputs are present); agents must know which key to read

---

## ADR-007: Structured JSON Logging over print() or Standard Formatter

**Decision:** All logging uses a custom `StructuredFormatter` that emits newline-delimited JSON. Extra fields are attached via `logging.info(..., extra={...})`.

**Context:** Plain-text logs are not queryable at scale. JSON logs ship directly to Datadog, CloudWatch, Loki, or any other aggregator without a parsing step.

**Consequences:**
- Log entries are machine-readable and filterable by `task_id`, `workflow_id`, `agent`, or any custom field
- The `@timed` decorator adds `duration_seconds` automatically to any wrapped method
- Local development output is less readable than formatted text; a dev-mode formatter can be added as a future enhancement
