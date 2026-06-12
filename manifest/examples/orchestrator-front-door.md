# Orchestrator Front Door — persistent multi-agent assistant

## Context
Cortex has a growing set of independent agent workflows (IPD report, report generation, client diagnostics, and the alert agents: IPS breach, house view, benchmark deviation), each a self-contained LangGraph graph registered in `app/workflows/registry.py`. Today the home-page chat is fronted by a **stateless supervisor** (`routers/supervisor.py` + `services/supervisor.py`) that does a single `classify()` LLM call and emits a `workflow_redirect` to exactly one workflow (its own thread). There is no way to run several agents for one task and merge their results, and no persistent conversation that can escalate from a chatbot turn → one agent → coordinating several.

The goal is an **orchestrator layer** that lets these (and future) agents be coordinated — for a single user task, the relevant agents do their part and the result is synthesized together. After a design discussion (grounded in the team's A2A brief, `data/A2A_Communication.pdf`), the chosen shape is a **persistent assistant**: a single long-lived orchestrator graph is the front door for all home chat, with the existing classifier demoted to a cheap short-circuit node inside that graph.

This manifest captures the design and the build order. It is a design-first task; code does not start until the plan is agreed.

### Decisions
1. **Evolve, don't rewrite** — keep the checkpointed-LangGraph + registry + Langfuse-tracing foundation; add an orchestrator tier on top — captured 2026-06-09.
2. **Pattern = pure orchestrator–worker + blackboard** — workers never talk to each other; only the orchestrator dispatches. Counterweight to the dynamic planner — captured 2026-06-09.
3. **Decomposition = LLM planner at runtime** — an orchestrator LLM reads the request + registry agent-cards and picks which workers to run (not fixed recipes) — captured 2026-06-09.
4. **Execution = both sync and background** — light tasks stream live via the existing SSE driver; heavy tasks run detached on the checkpointer and notify via the alerts system on completion — captured 2026-06-09.
5. **Workers are in-process only** — all agents stay LangGraph subgraphs in cortex; `fin`/`ledger` remain tool/data providers. No A2A/ACP network protocol; registry = discovery, shared state = transport. MCP stays for tools — captured 2026-06-09.
6. **Entry model = persistent assistant, orchestrator-as-front-door** — every home-chat turn enters one long-lived checkpointed orchestrator thread; `classify()` becomes a cheap routing/short-circuit node so chatbot and single-agent turns skip planning/blackboard. Supersedes the alternative "keep supervisor + orchestrator as two separate tiers" — captured 2026-06-09.
7. **Worker split: autonomous vs interactive** — read-only analytical agents (client_diagnostics, ips_breach, house_view, benchmark_deviation) fan out in parallel via headless `ainvoke`; interactive document-builders (ipd_report, report_generation) are wired as **subgraph nodes** so their `interrupt()` gates propagate up to the user through the orchestrator's existing driver — captured 2026-06-09.
8. **Dynamic planning + static wiring** — all workers wired into the orchestrator graph at build time; the planner's output drives conditional routing / `Send` fan-out among pre-wired nodes (you can't add subgraph nodes at runtime) — captured 2026-06-09.
9. **Blackboard store = MongoDB** — the checkpointer is `MongoDBSaver` (`app/db/checkpointer.py:70`), not Postgres; the blackboard goes in Mongo for consistency with checkpoints. Resolves Q1 — captured 2026-06-09 (from exploration).
10. **Step 2 split: build `run_worker` now, defer `stream_workflow` extraction** — the SSE driver in `routers/threads.py` is a ~290-line generator deeply coupled to web events / Langfuse spans / thread-metadata upserts; nothing depends on extracting it yet (the orchestrator needs the *headless* path). So `run_worker` is new isolated code; the hot-path refactor is deferred to the front-door layer that actually needs it. Minimal blast radius — captured 2026-06-09.
11. **Thread lifecycle = per-turn task on a persistent thread** — each orchestrator turn mints a new `task_id` and runs route→…→END; the thread provides FE continuity. True cross-task conversation memory + checkpoint-trim deferred (artifacts are already off-checkpoint in the blackboard). Resolves Q2/Q3 — captured 2026-06-09.
12. **Chatbot turns = handoff/redirect** (not inline) — inline chatbot would pull the separate chatbot service into the orchestrator; deferred. Resolves Q4 — captured 2026-06-09.
13. **Single-agent split** — autonomous single-agent runs inline via `run_worker` (true in-thread persistence, no gates); interactive single-agent (ipd/report-gen) hands off via redirect. Subgraph-composition-with-interrupt-propagation deferred (untestable without live env). Resolves Q5 — captured 2026-06-09.
14. **Front-door cutover gated/deferred** — the orchestrator is built to BE the front door (route classifier + branches), but `routers/supervisor.py` is NOT flipped to route all home chat through it in this layer. Cutover is a later flag flip after live validation, keeping the production hot path untouched now — captured 2026-06-09. **DONE (flag) 2026-06-09:** see Decision 15.
15. **Cutover flag = `orchestrator_front_door`, auto-ON for `local`** — `settings.orchestrator_front_door: bool|None=None` with `resolved_orchestrator_front_door` (mirrors `resolved_codeact_sandbox_mode`): unset → ON for `environment=local`, OFF for dev/prod; `ORCHESTRATOR_FRONT_DOOR=true|false` overrides. When ON, supervisor `POST /chat` redirects all home chat to `orchestrator` (skips `classify()`); the orchestrator's `route` node classifies. User runs local → using the new front door immediately; dev/prod stay safe until explicitly enabled. Reversible with no redeploy — captured 2026-06-09.

## Architecture

Target shape — one persistent, checkpointed orchestrator graph is the front door for all home chat. `route` (the demoted `classify()`) keeps trivial turns cheap; only `multi_agent` turns reach planning + fan-out. Workers split into autonomous (headless `ainvoke` fan-out) and interactive (wired as subgraph nodes so their `interrupt()` gates propagate up to the user). Pure orchestrator–worker — workers never call each other.

```
                         home chat (one long-lived, checkpointed thread per conversation)
                                                  │
                                                  ▼
        ┌─────────────────────────────────────────────────────────────────────────────┐
        │  ORCHESTRATOR GRAPH  (registered workflow · Postgres checkpointer · Langfuse) │
        │                                                                               │
        │     ┌──────────────┐                                                          │
        │     │   route      │  ← classify() short-circuit (CLASSIFIER_MODEL, cheap)    │
        │     └──────┬───────┘                                                          │
        │            │                                                                  │
        │   ┌────────┼─────────────────────────────┐                                   │
        │   │ chatbot│ single_agent      multi_agent│                                   │
        │   ▼        ▼                              ▼                                   │
        │ ┌──────┐ ┌──────────────┐        ┌────────────┐                              │
        │ │answer│ │ handoff /    │        │   plan      │ ← LLM planner reads          │
        │ │inline│ │ subgraph node│        │ (validated, │   agent-cards from registry  │
        │ └──────┘ └──────────────┘        │  bounded)   │                              │
        │                                  └─────┬───────┘                              │
        │                                        ▼                                      │
        │                                  ┌────────────┐   parallel where independent  │
        │                                  │  dispatch  │───────────────┐               │
        │                                  └─────┬──────┘               │               │
        │                                        ▼                      ▼               │
        │                                  ┌────────────┐        ┌────────────┐         │
        │                                  │  gather    │◄───────│  workers    │         │
        │                                  └─────┬──────┘        └────────────┘         │
        │                                        ▼                                      │
        │                                  ┌────────────┐   ┌──────────┐                │
        │                                  │ synthesize │──►│  verify  │──► answer       │
        │                                  └────────────┘   └──────────┘                │
        └───────────────────────────────────────┬───────────────────────────────────────┘
                                                 │
              ┌──────────────────────────────────┼───────────────────────────────────┐
              │ AUTONOMOUS workers (read-only)    │      INTERACTIVE workers          │
              │ headless ainvoke · fan-out        │      subgraph nodes · interrupts  │
              │                                   │      propagate to user            │
              ▼                                   ▼                                   ▼
        ┌─────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐        ┌──────────────┐
        │client_      │ │ips_breach│ │house_view│ │benchmark_    │        │  ipd_report  │
        │diagnostics  │ │          │ │          │ │deviation     │        │  report_gen  │
        └──────┬──────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘        └──────┬───────┘
               │             │            │              │                       │
               └─────────────┴────────────┴──────────────┴───────────────────────┘
                                          │  write artifacts (ids/frames, not prose)
                                          ▼
                        ┌──────────────────────────────────────────┐
                        │  DURABLE BLACKBOARD  (task_id-scoped)      │  ← synthesize reads here
                        └──────────────────────────────────────────┘

  Tools/data (in-process, via tool layer):  fin-wrappers · ledger · Pinecone · Redshift   (MCP, not A2A)

  Execution:  light task → stream live (SSE driver, runtime.stream_workflow)
              heavy task → detached run on checkpointer → persist results → raise ALERT as landing

  Shared catalog:  registry.py agent-cards (capabilities/when_to_use + input/output schema)
                   read by BOTH route(classify) and plan(LLM planner)
```

## Exploration Results
_(grounded in reads during the design session)_

### Consumers / callers
- `routers/supervisor.py` — `POST /chat`: calls `services.supervisor.classify(query, org_id)`, emits `thread_id`, `agent_context`, then `workflow_redirect` (non-chatbot intent) or `chatbot_redirect`. Stateless; thread id `supervisor-{user_id}`; no checkpointer.
- `services/supervisor.py:27` — `classify()`: resolves org slug → `get_enabled_workflows(org_slug)` → `build_supervisor_prompt` + `build_classification_model([ids])` → one `structured_completion` with `CLASSIFIER_MODEL`. Returns `chatbot` on failure. `ROUTING_EXCLUDED_WORKFLOWS = {"client_diagnostics"}` — already excluded from supervisor surfacing but reachable directly (the seam for orchestrator-dispatched workers).
- `routers/threads.py` — the **driver**: builds graph from registry (`get_workflow(name).build_graph(checkpointer=get_checkpointer())`, ~line 168/250), runs via `_astream_with_modes` (line 753), detects `__interrupt__` (line 354), maps interrupt value via `reg.interrupt_handler` → SSE (line 388), resumes with `Command(resume=reg.resume_transformer(message))` (line 268). Postgres checkpointer. This run-loop is inline in the router and is the thing to factor out.

### Data shape / schema
- `app/workflows/registry.py` — `WorkflowRegistration` dataclass: identity (name/slug/display_name/description/category), `build_graph`, SSE formatters, `initial_state_builder` (input only — **no output schema today**), `resume_transformer`, `interrupt_handler`, `cross_node_keys`, `thread_data_keys`, `extract_pending_state`, `history_formatter`, `payload_formatter`. `register_workflow` / `get_workflow` / `get_workflow_by_slug` / `get_all_workflows`.
- Workers:
  - `app/workflows/ipd_report/graph.py` — pipeline with human gates: `llm_intake → ask_file → parse_and_match → review_matches_gate → … → report_review_gate → finalize`. **Interactive.**
  - `app/workflows/report_generation/graph.py` — pipeline + subgraphs/builders. **Interactive.**
  - `app/workflows/client_diagnostics/` — codeact engine (1388-line `codeact.py`), starts with no DataFrames, accumulates via `tool_data` from fin-wrapper tool `stash`. **Autonomous.**
  - `app/workflows/alerts/{benchmark_deviation,house_view,ips_breach}/` — codeact engines seeded from an alert document; `intent_router.py` + `registration.py` shared. **Autonomous.**
- `client_diagnostics/tool_data_store.py` — process-local, per-workflow accumulator. The blackboard seed; must become durable + task-scoped for background + cross-agent use.

### Related subsystems
- `app/observability/tracing.py` — `tracing_scope(thread_id, user_id, request_id, workflow)` already wraps supervisor classify into Langfuse. Extend with correlation IDs across orchestrator→worker calls.
- `alerts/` workflows — candidate **landing experience** for completed background tasks (raise an alert → user clicks → lands in finished thread). Reuse, no new notification infra.

### Out of scope
- Google A2A / IBM ACP protocols (in-process only — Decision 5).
- Rewriting any worker graph's internals.
- Replacing the checkpointer or SSE transport.

### Not found
- No output/result contract on `WorkflowRegistration`.
- No headless worker-invocation path (everything assumes SSE + human resume).
- No cross-workflow / durable blackboard.

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

## Plan

### orchestrator/agent-cards-and-runtime
- [x] **Step 1 — Agent-card fields on registration** `app/workflows/registry.py`
  - Added `input_schema`/`output_schema` (type|None), `capabilities`/`when_to_use` (str), `interaction: Literal["autonomous","interactive"]="interactive"`, `output_extractor`. Plus `planner_capabilities(reg)` helper (capabilities → description fallback).
  - Backfilled `interaction="autonomous"` on the 4 read-only workers (client_diagnostics + 3 alerts); client_diagnostics fully populated as exemplar (capabilities + when_to_use). ipd_report / report_generation keep the `interactive` default → no edit.
  - Verified: all 6 register, defaults preserved, fallback works. ✅
- [x] **Step 2 (refined) — Headless `run_worker`** `app/workflows/runtime.py` (new)
  - `run_worker(name, payload, *, parent_thread_id, user_id, request_id) -> WorkerResult`. Rejects non-autonomous workers; runs on a child checkpoint thread; validates input/output against schemas when present; extracts via `output_extractor`; maps unexpected interrupt → `status="needs_input"`, `errors` → `failed`, exceptions → `failed`.
  - `stream_workflow` extraction from `routers/threads.py` **deferred** (Decision 10) — not needed until the front-door layer.
  - Verified: imports, async, contract-level. ⚠️ NOT yet run against a live worker (needs Mongo + OpenAI).

### orchestrator/durable-blackboard
- [x] **Step 3 — Task-scoped artifact store** `app/workflows/orchestrator/blackboard.py` (new)
  - Mongo collection `orchestrator_blackboard`, keyed by **`(task_id, step_id)`** (NOT `worker` — a plan can dispatch the same worker twice; see ⚠️ below). `put_artifact`/`get_artifacts`/`clear_task` + `ensure_indexes` (wired into lifespan).
  - ⚠️ **Did NOT migrate `tool_data_store`** onto it — that store is process-local *by design* to keep multi-thousand-row tool data out of the checkpoint (BSON-16MB). The blackboard holds bounded worker *artifacts* only. Decision refined.

### orchestrator/graph-hardcoded-plan
- [x] **Step 4 — Orchestrator graph skeleton** `app/workflows/orchestrator/{graph,state,sse_formatter,__init__}.py` (new)
  - Nodes `route → plan → dispatch → gather → synthesize → verify`. `route` always `multi_agent` (skeleton); `plan` hardcoded to a 2-step parallel fan-out via `client_diagnostics` (the only no-alert-seed autonomous worker) — diagnostics+ips_breach deferred to the LLM planner since ips_breach needs an `alert_id` seed. `dispatch` runs workers concurrently (`asyncio.gather` → `run_worker`), writes artifacts to blackboard; `synthesize` deterministic (no OpenAI dep); `verify` requires ≥1 completed.
  - Registered in `lifespan.py`; added `output_extractor=extract_output` to client_diagnostics (bounds its blackboard artifact to chat_message+tables+source_query).
  - Verified E2E (stubbed run_worker + in-memory blackboard): 2 distinct artifacts, parallel dispatch, merged answer, mixed-failure + all-fail verify paths. ✅ ⚠️ Not run against live Mongo/OpenAI.

### orchestrator/llm-planner
- [x] **Step 5 — LLM planner + rails** `app/workflows/orchestrator/planner.py` (new) + `graph.py`, `constants.py`
  - `plan_task(message)`: `structured_completion` over a dynamic response model whose step `worker` is a **`Literal` of autonomous worker names** (interactive workers structurally unselectable — discovery + least-capability at the type level). Rails: cap at `MAX_STEPS=4` (excess dropped + logged), empty/error → single `client_diagnostics` fallback (mirrors supervisor `classify()` fallback discipline).
  - `synthesize_answer(message, gathered)`: LLM merge of completed artifacts (integrate, keep figures, no invented numbers); deterministic-concat fallback on LLM failure.
  - Models: added `ORCHESTRATOR_PLANNER_MODEL` (`gpt-5.4-mini`) + `ORCHESTRATOR_SYNTHESIS_MODEL` (`gpt-5.5`) to constants.
  - `graph.py`: `plan_node` → `plan_task`; `synthesize_node` → `synthesize_answer`.
  - Verified (stubbed `structured_completion`): autonomous-only Literal excludes ipd/report-gen; cap to 4; empty→fallback; exception→fallback; LLM-synth vs deterministic fallback; full graph integration (plan 2 distinct workers → parallel dispatch → LLM synthesis). ✅
  - ⚠️ **Deferred within Step 5**: (a) `verify` is still structural (≥1 completed) — the *LLM number-guardrail* verifier is not built; (b) the **≤1 re-plan loop** (verify-fail → re-plan) is not wired (single planning pass today); (c) per-worker payload contracts — every step maps to `{"query": ...}`, which only `client_diagnostics` truly consumes (alert workers need `alert_id`); the prompt steers the planner away from alert agents for free-text, but a real `input_schema`-driven payload mapping is a follow-up.

### orchestrator/persistent-front-door
- [x] **Step 6 (scoped) — Front-door route + short-circuit** `app/workflows/orchestrator/{route,graph,state,sse_formatter}.py`
  - `route.py` (new): `classify_route(message, org_id) -> RouteDecision(mode, worker)` — one cheap `CLASSIFIER_MODEL` structured pick over 3 modes; `worker` is a `Literal` of the org's enabled-workflow ids (reuses `resolve_org_slug` + `get_enabled_workflows`). Degrades to `multi_agent` on failure (planner has its own fallback). `single_agent` without a valid worker → `multi_agent`.
  - `graph.py`: `route_node` resolves the branch — multi_agent→`plan`; single_agent+autonomous→pre-seed a 1-step plan and reuse `dispatch→gather→synthesize→verify`; single_agent+interactive (ipd/report-gen) or chatbot→`handoff_node`→END. Conditional edges `{multi_agent:plan, single_agent:dispatch, handoff:handoff}`.
  - `sse_formatter.py`: `handoff` node emits `workflow_redirect` / `chatbot_redirect` (same event names the supervisor uses).
  - Verified (stubbed classify/planner/run_worker/blackboard): all 4 branches route correctly; single-agent reuses the pipeline; handoffs set the right redirect; classify_route mode-mapping + fallbacks; SSE emits redirects; graph compiles with all 7 nodes. ✅ (Test-stub bug found+fixed: `structured_completion`'s 2nd positional is `response_model`, not `model`.)
  - ⚠️ **DEFERRED (need live env / FE contract — Decisions 12-14):** (a) flipping `routers/supervisor.py` to route ALL home chat through the orchestrator — NOT done; supervisor untouched, cutover is a later flag flip; (b) interactive workers as true in-thread **subgraph nodes with interrupt propagation** — handoff/redirect used instead; (c) the `workflow_redirect`/`chatbot_redirect` events from within a *threads-router* stream are not verified against the FE redirect contract (only the supervisor `/chat` stream is known to emit them today); (d) cross-task conversation memory / checkpoint-trim (Q2/Q3).

### orchestrator/background-and-landing
- [x] **Step 7 — Background execution + landing record** `app/workflows/orchestrator/{task_store,background}.py` (new) + `graph.py`, `lifespan.py`
  - `task_store.py`: Mongo `orchestrator_tasks` — durable per-task lifecycle (running/completed/failed + final_answer + thread_id) = the landing record. `background.py`: `HEAVY_STEP_THRESHOLD=3`; `dispatch_plan` (shared fan-out, DRY with `dispatch_node`); `run_task_background` (detached: dispatch→synthesize→persist→notify); `_notify_complete` seam.
  - `graph.py`: `_decide_exec` (plan size) after `plan` → `{foreground: dispatch, background: background}`; `background_node` records the task, spawns `asyncio.create_task(run_task_background)`, returns a "started — I'll notify you" message → END. `dispatch_node` refactored onto `bg.dispatch_plan`. `lifespan.py`: `task_store.ensure_indexes()`.
  - Verified: decision threshold; heavy→background (record+spawn, dispatch skipped); light→foreground; `run_task_background` completed→`mark_completed` + all-fail→`mark_failed`. **12 pytest tests** in `tests/workflows/orchestrator/test_orchestrator.py`, all green; 107 tests across edited suites pass (no regression).
  - ⚠️ **DEFERRED:** (a) actual **alert/inbox notification** — cortex has NO alert-creation path (alerts are produced upstream by Dagster, read-only here), so `task_store` IS the durable landing record and `_notify_complete` just logs; surfacing a clickable alert needs product + FE. (b) **Crash-safety** — the detached task is an in-process `asyncio` task (per-worker runs are checkpointed, but a process death leaves the task-level record `running`); a durable queue / checkpoint-resume is the follow-up.

## Open questions
1. Blackboard backing store — Postgres (alongside checkpointer) or Mongo (alongside enterprise_config)? -> **Mongo** (checkpointer is MongoDBSaver; Decision 9).
2. Persistent thread lifecycle — one thread per user forever, or per-conversation/per-session with explicit "new task" boundaries? Affects state-growth/trim strategy. -> **Per-turn task on a persistent thread for now** (new `task_id` each turn; cross-task conversation memory deferred). Decision 11.
3. State-growth strategy for the long-lived orchestrator thread — summarize/trim conversation memory separately from the task blackboard? -> **Deferred** (artifacts already off-checkpoint in the blackboard; conversation-memory trim is a follow-up). Decision 11.
4. Should chatbot turns run as an inline node in the orchestrator, or hand off to the existing chatbot path? -> **Handoff/redirect** for now (inline chatbot deferred). Decision 12.
5. For single-agent turns in the persistent model — handoff (today's redirect) or run the agent as a subgraph node inside the orchestrator thread? -> **Split: autonomous single-agent runs inline (`run_worker`) in the orchestrator thread; interactive single-agent hands off** (subgraph-with-interrupt-propagation deferred — needs live testing). Decision 13.

## Confirmed findings
- ⚠️ **Registration is explicit in `app/lifespan.py:109-127`**, NOT via `app/workflows/__init__.py`. `register_all()` + `_WORKFLOWS` there is stale (lists only ipd_report + report_generation) and has no callers. To register in a script/test, call each module's `register()` as lifespan does. The front-door layer must add the orchestrator's `register()` to lifespan too.
- ⚠️ **Checkpointer is `MongoDBSaver`** (`app/db/checkpointer.py:70`), not Postgres — drove Decision 9 (blackboard in Mongo). CLAUDE.md mentions Postgres+Mongo+Redshift; checkpoints specifically are Mongo.
- Confirmed: `WorkflowRegistration` is purely additive-safe — the 6 existing registrations construct unchanged with the new defaulted fields.
- Confirmed: `interaction` default `"interactive"` preserves behavior for ipd_report / report_generation (they're never auto-fanned-out).
- Not yet confirmed (needs live env): `run_worker` executing an autonomous worker end-to-end; nested subgraph interrupt propagation for interactive workers through the `threads.py` driver. These are the first probes for the next layers.
- Tooling: `ruff` is not installed in `.venv`; used `py_compile` for the syntax gate. No `.env` in repo (`.env.demo`/`.env.example` only) — Settings needs env injected to import.

## Testing plan
_(to populate)_ — parity: SSE output for an existing single-workflow turn must be byte-identical after the `runtime.py` extraction (Step 2 is behavior-preserving). Canary: one 2-worker orchestrated task end-to-end (Step 4). Interrupt check: drive IPD as a subgraph node and confirm `review_matches_gate` reaches the user and resume routes back (Step 6).

## Rollout plan
_(to populate)_ — orchestrator gated behind an org/feature flag in `enterprise_config.agentic_config`; existing supervisor path remains the default until the front-door swap (Step 6) is validated. Rollback = config flip, no redeploy.

## Review

### Files changed (layer: agent-cards-and-runtime)
- `app/workflows/registry.py` — added agent-card fields (`interaction`, `capabilities`, `when_to_use`, `input_schema`, `output_schema`, `output_extractor`) to `WorkflowRegistration` (all defaulted, additive); added `planner_capabilities()` helper. Imported `Literal`.
- `app/workflows/runtime.py` — **new**. Headless `run_worker()` + `WorkerResult` dataclass for orchestrator dispatch of autonomous workers.
- `app/workflows/client_diagnostics/__init__.py` — `interaction="autonomous"` + capabilities/when_to_use (exemplar).
- `app/workflows/alerts/{benchmark_deviation,ips_breach,house_view}/__init__.py` — `interaction="autonomous"`.

### Files changed (layers: durable-blackboard + graph-hardcoded-plan)
- `app/workflows/orchestrator/blackboard.py` — **new**. Mongo `orchestrator_blackboard`, keyed `(task_id, step_id)`; put/get/clear + indexes.
- `app/workflows/orchestrator/state.py` — **new**. `OrchestratorState` + `PlanStep` (with `step_id`); lightweight `worker_status`, full artifacts in blackboard.
- `app/workflows/orchestrator/graph.py` — **new**. route→plan→dispatch→gather→synthesize→verify; hardcoded plan, parallel dispatch, deterministic synthesis.
- `app/workflows/orchestrator/sse_formatter.py` — **new**. Coarse phase/status + final markdown.
- `app/workflows/orchestrator/__init__.py` — **new**. `register()` + `build_initial_state` (generates `task_id`).
- `app/lifespan.py` — register orchestrator + `ensure_indexes()` for the blackboard.
- `app/workflows/client_diagnostics/__init__.py` — `extract_output()` + `output_extractor=` on registration.

### Files changed (layer: llm-planner)
- `app/workflows/orchestrator/planner.py` — **new**. `plan_task` (autonomous-only Literal, cap, fallback) + `synthesize_answer` (LLM merge, deterministic fallback) + `autonomous_workers()`.
- `app/workflows/orchestrator/graph.py` — `plan_node`/`synthesize_node` now delegate to the planner.
- `app/constants.py` — `ORCHESTRATOR_PLANNER_MODEL`, `ORCHESTRATOR_SYNTHESIS_MODEL`.

### Files changed (layer: persistent-front-door)
- `app/workflows/orchestrator/route.py` — **new**. `classify_route` 3-way front-door classifier (enabled-workflow Literal, multi_agent fallback).
- `app/workflows/orchestrator/graph.py` — `route_node` resolves branch; `handoff_node` added; conditional edges multi/single/handoff.
- `app/workflows/orchestrator/state.py` — `selected_worker`, `handoff` fields; `route` semantics documented.
- `app/workflows/orchestrator/sse_formatter.py` — emit `workflow_redirect`/`chatbot_redirect` on handoff.

### Files changed (layer: background-and-landing)
- `app/workflows/orchestrator/task_store.py` — **new**. Mongo `orchestrator_tasks` lifecycle record.
- `app/workflows/orchestrator/background.py` — **new**. `dispatch_plan` (shared fan-out), `run_task_background` (detached), `_notify_complete`, `HEAVY_STEP_THRESHOLD`.
- `app/workflows/orchestrator/graph.py` — `_decide_exec` + `background_node`; `dispatch_node` refactored onto `bg.dispatch_plan`.
- `app/workflows/orchestrator/sse_formatter.py` — render the background "started" message.
- `app/lifespan.py` — `task_store.ensure_indexes()`.
- `tests/workflows/orchestrator/test_orchestrator.py` — **new**. 12 tests (route/plan/decision/branches/background).

## Post-cutover fixes (after first UI run)

⚠️ **UI run exposed two bugs** (the handoff/lifecycle seams): (1) orchestrator ran to `END` with no interrupt → thread **finalized after one turn** ("thread has been finalized"); (2) `workflow_redirect`/`chatbot_redirect` emitted from the threads stream are **silently dropped** — `legacy_event_to_web_events` (`app/presentation/web.py`) has no case for them.

**Fixes (16):**
- **Multi-turn persistence** — added an `await_input` node that `interrupt()`s after every turn (re-arms composer, thread stays `waiting_for_input`) and loops back to `route` with the next message + fresh `task_id`. No more bare `END`/finalize. Mirrors the codeact `agent_gate` pattern.
- **Inline answers, no redirects** — chatbot turns answered inline (`planner.answer_chatbot`); interactive workers (ipd/report-gen) get an inline pointer to their guided workflow instead of a dropped redirect. Supersedes Decisions 12-13's redirect approach.
- Graph: `route → {plan|dispatch|chatbot|handoff}`, all terminal branches → `await_input` → `route`. Tests use `MemorySaver` (interrupt needs a checkpointer); added `test_thread_stays_alive_across_turns` (resume regression). **13 orchestrator tests green.**

**Monitoring-section card (17):** orchestrator added to `org_config/dev/{default,waterfield}_org.json` `agentic_config.workflows` with `category=monitoring` (clean diff, UTF-8 preserved); `ROUTING_EXCLUDED_WORKFLOWS += "orchestrator"` (front door, not a classify target — like client_diagnostics); registry category → `monitoring`; `chat-widget` `WorkflowType` union gained `'orchestrator'` (tsc green). Clicking the card opens an orchestrator thread directly (no supervisor). **116 tests pass across edited suites.**

**Interactive-worker handoff now works (19):** the inline-pointer dead-end ("open it from the Workflows panel") is replaced by a real hand-off. Root cause was the web-channel translation (`app/presentation/web.py` `legacy_event_to_web_events`) dropping `workflow_redirect` (fell through to `return []`). Fix: added a `workflow_redirect` passthrough case (additive — only the orchestrator emits it from a node). `handoff_node` now emits `workflow_redirect` carrying `original_message`, so "i want an IPD for atharva" opens a fresh IPD thread seeded with that message. Inline "Opening **X**…" is the fallback if the FE ignores it. Supersedes the inline-pointer half of Decision 13. Tests: `test_route_interactive_worker_hands_off` + `test_web_channel_passes_workflow_redirect_through`; 141 pass (excl. pre-broken ipd_report dir).

**Known behavior (18, ACCEPTED 2026-06-09):** the orchestrator routes ~everything to `client_diagnostics` because it's the ONLY general-purpose autonomous worker — the alert agents need an `alert_id` seed and aren't plannable from free text (the deferred `input_schema`-driven payload follow-up). User confirmed this is expected — leave as-is; the orchestrator earns broader value once more free-text-plannable autonomous workers exist. No change.

## In-thread embedding of interactive workers (Decision 20)

**Goal (user, 2026-06-09):** ONE Cortex Orchestrator agent serves everything — including IPD/report-gen — **inline in the same thread**, no redirect to a separate agent. Controlled by an **include/exclude list**. Redirect (Decision 19) is the interim; this supersedes it for included workflows. User chose a **staged, flag-gated build** (low risk; existing workflows untouched until validated).

**Architecture (LangGraph subgraph composition):**
- Included workflows are embedded as **subgraph nodes** in the orchestrator graph. `route` sends an embed-eligible interactive worker to its subgraph node; its `interrupt()`s (file upload, review gates) propagate up to the orchestrator thread; resumes route back down. One agent, one thread.
- **Include list** = `settings.orchestrator_embedded_workflows` (workers served in-thread); everything else falls back to redirect/standalone (the exclude side).

**Stage 1 (DONE 2026-06-09 — config + seam, test-verified):**
- `config.py`: `orchestrator_embedded_workflows: list[str] = []` (include list) + `orchestrator_embed_enabled: bool = False` (master gate). Empty/off = redirect everything (current behavior — existing workflows untouched).
- `route.py`: `embeds_inline(worker)` = gate-on AND worker ∈ include list.
- `graph.py`: `route_node` routes interactive workers to `embed` (if `embeds_inline`) else `handoff`; new `embed_node` is the in-thread seam — Stage-1 body falls back to the redirect + logs intent; `embed` wired into build_graph + sse_formatter (treated like handoff). Loops to `await_input`.
- Tests: `test_embeds_inline_respects_list_and_gate`, `test_interactive_worker_embeds_when_listed`, `test_interactive_worker_redirects_when_not_listed`. 34 orchestrator/supervisor/presentation tests green.

**Stage 2 (IMPLEMENTED 2026-06-09 — flag-gated, default ON for local; NEEDS live FE validation):**
- `config.py`: `orchestrator_embed_enabled` → tri-state, auto-ON for `environment=local`; include list default `["ipd_report","report_generation"]`.
- `graph.py`: each included+registered+interactive workflow compiled (checkpointer=None) and added as a real **subgraph node** `embed_<worker>`; `embed_seed` node bridges state via the SHARED `query` channel (added to `OrchestratorState`) + sets `active_embed`; `route "embed" → embed_seed → embed_<worker> → await_input`. Interrupts propagate natively (subgraph inherits the parent checkpointer).
- `routers/threads.py`: when `workflow==orchestrator` AND embed enabled → `astream(subgraphs=True)`; `_astream_with_modes` now yields `(namespace, mode, chunk)`; events from an `embed_<w>` namespace are formatted by **that workflow's** `format_node_events` (`_resolve_ns_workflow`); interrupts delegate to the embedded workflow's `interrupt_handler` (via `active_embed`). Non-orchestrator / embed-off streams are byte-identical (empty namespace path).
- Verified: orchestrator builds with IPD + report-gen embedded as real subgraphs (local); 166 tests pass, 9 failures all pre-existing (`test_workflows_list` ×5 + supervisor schema ×4 — fail on clean tree).
- ⚠️ **NOT live-verified** (the whole point of the flag): whether IPD's `ask_file`/review-gate interrupts render + resume correctly *through the orchestrator thread* in the real widget, and whether namespaced subgraph SSE renders IPD's tables. This is what the user is testing now.

**Stage-2 fixes after first live run (Decision 21):**
- ⚠️ **Raw `{'type':'ask_file'}` leaked as chat text** — IPD's interrupt surfaced at the TOP level (empty namespace), so the driver used the *orchestrator's* interrupt_handler (which `str()`s it) instead of IPD's. Fix: interrupt handling now resolves the handler from `active_embed` (authoritative) for BOTH the captured-value and snapshot-task branches.
- ⚠️ **Upload not landing** ("No file was received") — `_has_pending_file_ask` only scanned top-level tasks; an embedded IPD's `ask_file` is nested. Fix: `aget_state(subgraphs=True)` + recursive `_snapshot_has_ask_file`.
- **CD/alerts (user question):** generalized embedding — `embedded_workers()` now embeds ANY registered workflow on the include list (not just interactive); `route_node` checks `embeds_inline` FIRST so single-agent serves the worker's FULL experience in-thread. Added `client_diagnostics` to the default include list (its rich multi-turn UI now runs in-thread instead of the flattened headless-dispatch). `embed_seed` seeds both bridge channels (`query` for IPD, `messages` for CD). **Alerts stay alert-triggered** (seeded by `alert_id` from the Alerts panel, not a free-text orchestrator turn) — not embedded by default.
- Verified: orchestrator builds with IPD + report-gen + client_diagnostics embedded; 38 orchestrator/supervisor/presentation + 7 routers tests pass.

**Route mis-classification fix (Decision 22):** CD-type questions ("how is the Sharma family doing?", "AUM for X") were classified as **chatbot** (→ generic "name the client" answer) instead of single_agent→client_diagnostics. Cause: `classify_route` used a generic 3-bucket prompt lacking the per-workflow `classifier_hint`s the supervisor uses. Fix: `route.py` now builds a hint-rich prompt from the enabled workflows (id + description + classifier_hint) and explicitly says "if it matches an agent's when-to-use, choose single_agent NOT chatbot, even if conversational." `_enabled_worker_ids` → `_enabled_workers` (full entries). 21 orchestrator tests pass.

**Multi-intent + interactive-followup (Decision 23, "improve detection, note the report"):** a request like "asset breakdown (CD) + overview report (report-gen)" collapsed to CD only, because (a) the classifier under-detected multi-intent and (b) `report_generation` is interactive → not headless-fan-out-able (planner Literal is autonomous-only). Fix (user chose low-effort): route prompt now picks `multi_agent` when ≥2 distinct deliverables / 'and'-joined asks; planner returns `followups` (interactive workflow ids it can't run, a separate Literal field) alongside autonomous `steps`; `synthesize_node` appends "_To finish, open **Report Generation** from the Workflows panel_". `plan_task` now returns `PlanResult(steps, followups)`. Interactive deliverables are NOT auto-generated (accepted) — pointed to instead. True mixed orchestration (sequence fan-out → embedded interactive) deferred. 157 tests pass.

**Mixed orchestration — all in one agent (Decision 24):** the "open Report Generation from the panel" pointer is replaced by running it INLINE. After the autonomous analysis (CD) synthesizes, `verify` conditionally routes (`_route_after_verify`) to `embed_seed` → the interactive followup's subgraph (e.g. report_generation), sequenced in the SAME thread. `synthesize_node` sets `pending_embed` for the first embeddable followup (and only NOTES non-embeddable ones / when embed is off). So "asset breakdown AND overview report" → CD analysis inline → report-gen runs inline next, all in the Cortex Orchestrator agent. Build_graph guards all embed wiring on `embeds` being non-empty. 48 tests pass. This is the "serve all in one agent interface" goal — single-agent (IPD/report-gen/CD embedded) AND multi-agent-with-interactive (sequenced) now run in-thread; only alerts (alert_id-seeded) remain panel-launched.

**"No worker produced a result" fix (Decision 25):** multi-agent dispatch of `client_diagnostics` via headless `run_worker` returned `needs_input` — CD answers then parks on its `agent_gate` await-next-turn interrupt, and `run_worker` checked the interrupt BEFORE extracting output, discarding the answer → empty `gathered` → "No worker produced a result." Fix: `run_worker` now extracts output FIRST; if `_has_output` (any truthy value in the extracted dict), returns `completed` even with a pending interrupt (CD's answer-then-gate is normal); only `needs_input` when there's a pending interrupt AND no usable output. Test: `test_run_worker_keeps_output_despite_await_interrupt`. 152 tests pass.

**Conversational continuity (Decision 26):** orchestrator router was stateless per turn — a bare-name follow-up ("Arundhati Dandekar") after a clarification routed to chatbot. Fix: `await_input` captures each finished turn (user msg + assistant answer / `[<worker> handled this]`) into a capped `route_history`; `route_node` feeds it to `classify_route`, whose prompt now says short clarifications continue the prior specialist (NOT chatbot), while NEW explicit requests are classified fresh (so it doesn't over-stick). Test: `test_thread_stays_alive_across_turns` asserts turn-2 history flows.

**Report-vs-CD tie-breaker (Decision 27):** "create an overview report for X" routed to client_diagnostics (its hint claims "overview") instead of report_generation. Fix: route prompt tie-breaker — "generate/create/build a 'report' → report-generation, NOT diagnostics, even with 'overview'/'breakdown'; diagnostics is for quick overview/AUM questions without a generated report." 42 tests pass.

**Multi-agent dispatch bugs from live logs (Decision 28):** (a) `DuplicateKeyError` — a stale `(task_id, worker)` unique index from the pre-step_id blackboard schema persisted in Mongo and rejected a plan that dispatched `client_diagnostics` twice. Fix: `ensure_indexes` drops `task_id_1_worker_1` if present. (b) Headless workers called ledger with empty `organization_id`/`user_id` (→ 400 → entity not found, e.g. "Dandekar"), because `run_worker` seeded the worker's initial state from the plan payload (`{query}` only). Fix: `run_worker` gained an `org_id` param and injects `{user_id, org_id}` into the payload; threaded through `dispatch_plan` / `dispatch_node` / `run_task_background` / `background_node`. This is why embedded single-agent CD found entities but headless multi-agent CD didn't. 42 tests pass. (Note: the embedded report-gen followup already worked — it runs in-thread with identity from state — and produced a full overview report in the live run.)

**Native sequenced rendering + response-mode toggle (Decision 29):** the LHS showed the orchestrator's LLM-synthesized markdown (CD flattened) instead of CD's native chart/table — because multi-agent ran CD headless + synthesized, while report-gen (embedded) rendered natively. User wants each agent to render its OWN output. Rewrite: multi-agent now builds an ordered, de-duped **`embed_queue`** of embeddable workers (plan steps + followups); `route → plan → embed_seed → embed_<w> → (more? embed_seed : await_input)` — each runs as a native subgraph in sequence, NO synthesis. Headless dispatch+synthesize remains only as the fallback for non-embeddable workers / synthesize mode. **Configurable** via `settings.orchestrator_response_mode`: `"native"` (default — agents render their own) vs `"synthesize"` (orchestrator merges headless data into one answer); `embeds_inline` gates on it. Removed `_decide_exec`/`_route_after_verify`/`pending_embed` logic. 153 tests pass.

**Planner under-queued report_generation (Decision 30):** "asset breakdown + overview report" ran only CD — the planner let CD absorb "overview" and didn't add report_generation to `followups`, so `embed_queue=[client_diagnostics]` only (report-gen never sequenced). Fix: planner prompt now MANDATES adding `report_generation` to followups when the request asks to generate/create/build/prepare a REPORT (CD does quick analysis, NOT formal report deliverables). With that, embed_queue=[client_diagnostics, report_generation] → both render natively in sequence. 26 tests pass.

**Perpetual-interrupt blocked sequencing → headless+replay for autonomous (Decision 31):** embedding CD before report-gen failed — CD is a PERPETUAL chat agent (its `agent_gate` interrupts to await the next turn and never reaches END), so embedded-CD captured the thread and report-gen never ran. Live logs confirmed: CD ran, hit `agent_gate` (interrupted), graph paused, report-gen skipped. New model: **only INTERACTIVE/terminating workflows (ipd_report, report_generation) embed as subgraphs; autonomous chat agents (CD) run headless + NATIVE REPLAY.** `embeds_inline`/`embedded_workers` now require `interaction=="interactive"`. Flow: `plan → dispatch (CD headless) → gather → replay (emit CD's own chat + tables natively, via its payload `components`) → verify → embed_seed (report-gen) → embed → await_input`. New `replay_node` + `_route_after_gather` (native→replay / synthesize→synthesize) + re-added `_route_after_verify` (embed_queue→embed). CD's native chart/tables now render via replay (no LLM-merge), report-gen embeds after — sequencing works because CD no longer captures the thread. 154 tests pass. ⚠️ Live-verify: the replay→embed handoff (CD tables render, then report-gen subgraph starts).

**Original Stage-2 plan (for reference):**
- `routers/threads.py` `_astream_with_modes`: add `subgraphs=True` (handle the namespaced 3-tuple) so a subgraph's internal nodes stream. **Gate behind a flag** (e.g. `orchestrator_embed_enabled`) — default off so every other workflow's stream is byte-identical until validated.
- Orchestrator `format_node_events`: detect namespaced sub-nodes (`ipd_report:<node>`) and **delegate** to that workflow's `format_node_events`.
- Orchestrator `interrupt_handler`: **delegate** to the active sub-workflow's `interrupt_handler` (IPD `ask_file` / review gate).
- State bridge: map orchestrator state → sub-workflow initial state (the sub-workflow's `initial_state_builder`) at entry.
- ⚠️ Risk: touches the shared production driver + SSE/interrupt contract for ALL workflows; namespaced-subgraph FE rendering is unverified without the live widget — hence the flag + staged validation.

## Review (overall — all 6 layers)

**What shipped.** A new `app/workflows/orchestrator/` package — a registered LangGraph workflow that is the persistent-assistant front door: `route` (cheap 3-way classify) → for multi-agent, `plan` (LLM planner over registry agent-cards, autonomous-only `Literal`, capped) → `dispatch` (parallel headless `run_worker`) → blackboard → `synthesize` (LLM merge) → `verify`; single-autonomous reuses that pipeline; chatbot / interactive workers hand off; heavy plans run detached with a durable task-store landing record. Foundation: agent-card fields + `output_extractor` on `WorkflowRegistration`, headless `run_worker` runtime, Mongo blackboard + task store.

**Status:** functionally verified with stubs (12 orchestrator tests + 107 across edited suites, no regression). NOT yet run against live OpenAI/Mongo.

**How to cut over (DONE — flag-gated, Decision 15):** `settings.orchestrator_front_door` gates it. **Auto-ON for `environment=local`** (so local dev uses the orchestrator front door now); OFF for dev/prod unless `ORCHESTRATOR_FRONT_DOOR=true`. When ON, `routers/supervisor.py` `POST /chat` redirects all home chat to the `orchestrator` workflow (skipping `classify()`). Rollback = `ORCHESTRATOR_FRONT_DOOR=false`, no redeploy. Enable on dev/prod after a live run.

### Files changed (cutover)
- `app/config.py` — `orchestrator_front_door` flag + `resolved_orchestrator_front_door` (auto-on for local).
- `app/routers/supervisor.py` — flag-gated branch: redirect to `orchestrator` (forwards `alert_id`), skip classify.
- `app/schemas/web.py` — added `"orchestrator"` to `WorkflowName` Literal (else direct `/threads/{id}/inputs` with `workflow=orchestrator` 422s).
- `tests/supervisor/test_router.py` — autouse fixture pins flag OFF for legacy tests + new `test_front_door_cutover_routes_to_orchestrator`.

### Frontend (chat-widget) — to see it on the UI
- `chat-widget/src/features/cortex/types/agent.ts` — added `'orchestrator'` to the `WorkflowType` union (the `workflow_redirect` handler in `agentStore.ts` is generic; no per-`WorkflowType` exhaustive map breaks; `tsc --noEmit` green). This lets the widget mint/open an `orchestrator` thread.
- Requires `agentic_config.enabled=true` for the user — `use-fetch-query.ts` drops `workflow_redirect` entirely when the flag is off.
- ⚠️ **Chatbot handoff won't render**: when the orchestrator's `route` picks `chatbot`, it emits `chatbot_redirect` mid-stream, which `agentStore` *intentionally ignores* (chatbot proxying only happens on the supervisor `/chat` path). So casual/chatbot queries via the front door produce no visible answer until either the orchestrator answers chatbot inline (Decision 12) or the widget handles `chatbot_redirect` in-stream. Demo with analytical/multi-agent queries, which synthesize inline and DO render.

### Testing (without the supervisor path)
Drive the orchestrator directly via the threads router — same path the FE uses post-redirect, supervisor never involved:
- Script: `tasks/orchestrator-front-door/artifacts/smoke_orchestrator.sh` — POSTs `/cortex/threads/{uuid}/inputs` with `workflow=orchestrator`, headers `x-user-id`/`x-org-id` + `Authorization: Bearer $SERVICE_AUTH_TOKEN`, streams SSE.
- Needs a running server (`uv run uvicorn app.main:app --port 8082`) with real OpenAI/Mongo/fin/ledger env and a real advisor `user_id`/`org_id` (the diagnostics worker fetches live data).
- ⚠️ Pre-existing unrelated test failures: `tests/supervisor/test_{schemas,prompt_builder,service}.py` (4) fail on a clean tree too (SupervisorClassification schema drift) — not from this work.

**Known follow-ups (all ⚠️ in Plan):** `stream_workflow` extraction; LLM number-guardrail verifier + ≤1 re-plan loop; `input_schema`-driven per-worker payloads (so alert workers are plannable with `alert_id`); interactive workers as true in-thread subgraph nodes (interrupt propagation) instead of handoff; FE redirect-contract verification from the threads stream; real alert/inbox notification; background crash-safety (durable queue); cross-task conversation memory/trim.

**Out of scope (held throughout):** A2A/ACP protocols (in-process only); rewriting worker internals; replacing checkpointer/SSE transport.

### Cutover / follow-ups
- **Reachable now** via threads router with `workflow="orchestrator"` — LLM plans autonomous workers from agent-cards, fans out in parallel, LLM-synthesizes. Not yet the front door (supervisor still routes single-agent; Step 6).
- Follow-ups surfaced by Step 5: LLM number-guardrail verifier; ≤1 re-plan loop; `input_schema`-driven per-worker payload mapping (so alert workers can be planned with `alert_id`).
- Live-verify gap: needs a run against real Mongo + OpenAI to confirm `run_worker` drives client_diagnostics to a populated `agent_final_payload` and the blackboard round-trips.
- Next: **Step 5 — LLM planner + rails** (replace hardcoded plan; validate against registry; bound count/re-plan; LLM synthesis + verify guardrail), then **Step 6 — front-door swap**.
- Out of scope so far: planner, front-door swap, background path.
