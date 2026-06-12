# Orchestrator Front Door — persistent multi-agent assistant

> A complex task — a persistent, checkpointed multi-agent orchestrator that becomes the front door for all home chat — decomposed into one tight bottom-up stack. Each layer answers a single reviewable question and can't be built until the layer below it is tested.

## Stack

```
orchestrator/agent-cards-and-runtime    ← implement first (registry contract + shared run-loop)
      ↑
orchestrator/durable-blackboard         (task-scoped artifact store)
      ↑
orchestrator/graph-hardcoded-plan       (route→dispatch→gather→synth→verify, fixed 2-worker plan)
      ↑
orchestrator/llm-planner                (swap hardcoded plan for planner + rails)
      ↑
orchestrator/persistent-front-door      (classify as short-circuit node; orchestrator owns home thread)
      ↑
orchestrator/background-and-landing     ← implement last (detached run + alert landing)
```

| Layer | What it does | Depends on | Reviewable question | Status |
|-------|-------------|------------|---------------------|--------|
| `orchestrator/agent-cards-and-runtime` | Add `input_schema`/`output_schema`/`capabilities`/`when_to_use`/`interaction` to `WorkflowRegistration`; extract `stream_workflow` + `run_worker` into `app/workflows/runtime.py` from `routers/threads.py` | — | Does `run_worker(client_diagnostics, …)` return typed data headless, with the SSE path unchanged? | open |
| `orchestrator/durable-blackboard` | Promote `tool_data_store` to a task-scoped, durable artifact store (Postgres/Mongo) keyed by `task_id` | agent-cards-and-runtime | Are artifacts structured (ids/frames), not prose, and readable across workers? | open |
| `orchestrator/graph-hardcoded-plan` | New orchestrator LangGraph: `route → plan(fixed) → dispatch → gather → synthesize → verify`; fan out 2 autonomous workers | durable-blackboard | Does a fixed 2-worker task stream a merged answer end-to-end? | open |
| `orchestrator/llm-planner` | Replace fixed plan with LLM planner reading agent-cards; add rails (validated bounded plan, ≤1 re-plan, least-capability, verify) | graph-hardcoded-plan | Are plans validated against the registry and bounded? | open |
| `orchestrator/persistent-front-door` | Orchestrator becomes home-chat front door; `classify()` as cheap short-circuit node (chatbot/single-agent skip planning); interactive workers wired as subgraph nodes (interrupt propagation) | llm-planner | Do trivial turns stay cheap; do IPD gates surface to the user? | open |
| `orchestrator/background-and-landing` | Heavy plans run detached on checkpointer; results persisted; completion raises an alert as the landing | persistent-front-door | Does a background task notify + land in its finished thread? | open |
