# Project Plan

## Objective

Build a production-quality multi-agent coordination framework that demonstrates the architecture and engineering judgment expected for Staff AI Engineer, Forward Deployed Engineer, and AI Platform roles.

---

## Milestones

### Phase 1 — Core Infrastructure (Complete)

- [x] Data models: `Task`, `WorkflowState`, `WorkflowResult`, status enums
- [x] `BaseAgent` abstract class with typed `execute()` contract
- [x] `Router` with registry-based dispatch and runtime override support
- [x] `StateManager` with state machine enforcement and thread safety
- [x] `TaskQueue` — thread-safe FIFO with batch operations
- [x] `Coordinator` — planning, dispatch, retry with exponential back-off
- [x] Structured JSON logging with `@timed` decorator
- [x] Three concrete agents: Research, Analysis, Reporting
- [x] Full test suite: routing, state, queue, coordinator, agents
- [x] `main.py` demo entry point with human-readable output

### Phase 2 — LLM Integration (Planned)

- [ ] Inject `anthropic.Anthropic` client into agents via optional constructor argument
- [ ] `ResearchAgent` calls Claude with tool use (web search, RAG retrieval)
- [ ] `AnalysisAgent` calls Claude to synthesize structured JSON insights
- [ ] `ReportingAgent` calls Claude to generate polished prose output
- [ ] Streaming support: pass `stream=True`, surface partial tokens as progress events
- [ ] Token usage tracking added to `WorkflowResult`

### Phase 3 — API Layer (Planned)

- [ ] FastAPI application with endpoints:
  - `POST /workflows` — submit a goal, return `workflow_id`
  - `GET /workflows/{id}` — poll execution history
  - `GET /workflows/{id}/stream` — SSE stream of task completion events
- [ ] Pydantic request/response schemas aligned with internal models
- [ ] OpenAPI documentation auto-generated

### Phase 4 — Persistence & Scale (Planned)

- [ ] `RedisStateManager` — swap in-memory store for Redis with TTL-based expiry
- [ ] `CeleryTaskQueue` — distributed worker pool for parallel agent execution
- [ ] Workflow DAG planner with topological sort for concurrent branches
- [ ] Dead letter queue for permanently failed tasks

### Phase 5 — Observability & Evaluation (Planned)

- [ ] OpenTelemetry traces: span per task, attributes for agent name, retries, duration
- [ ] Prometheus metrics: workflow throughput, task failure rate, p95 latency
- [ ] LLM-as-judge evaluation: score agent outputs against golden examples
- [ ] Confidence threshold gate: block pipeline progression if score < threshold

---

## Design Constraints

- **No framework lock-in**: core logic has zero runtime dependencies beyond the standard library
- **Testability first**: every component is dependency-injected; no patching required in tests
- **Incremental complexity**: each phase adds capability without requiring rewrites of prior phases
- **Production signals**: structured logging, typed errors, state machine enforcement from day one

---

## Open Questions

1. **Parallelism model**: Asyncio coroutines vs. thread pool vs. Celery workers — decision deferred until API layer is in place
2. **State persistence boundary**: Should workflow state survive process restart? Depends on deployment model (serverless vs. long-running service)
3. **Agent capability discovery**: Should the Router query agents for their supported task types, or remain a static registry?
4. **Human-in-the-loop integration**: Webhook callback vs. blocking queue poll for human review tasks
