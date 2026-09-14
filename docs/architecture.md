# Architecture

One level deeper than the README: component boundaries, the agent state machine, the data
model, and the request lifecycle.

## Design goals

1. **Reliable decisions.** The LLM drives the reasoning and proposes the decision, but must
   not invent numbers or take a forbidden action → deterministic tools own all math and a
   guardrail validates and can override the LLM.
2. **Genuine feedback loop.** The agent detects when an action's *actual* outcome differs
   from expectation and recovers → post-action validation re-reads persisted state and can
   loop back to re-plan.
3. **Runs anywhere.** Fully functional with no usable LLM key (deterministic planner) and
   with a local SQLite DB for tests; the app itself uses PostgreSQL (Neon).

## Component boundaries

| Layer | Module | Responsibility |
|---|---|---|
| API | `app/api/routes.py`, `app/main.py` | REST surface, request validation, CORS |
| Orchestration | `app/agent/graph.py`, `nodes.py`, `runner.py` | LangGraph state machine + HITL drive + logging |
| LLM tool schema | `app/agent/tools_schema.py` | Function specs + dispatch + `assess_purchase` |
| Decision policy | `app/agent/policy.py` | Pure map: analysis → decision (guardrail baseline) |
| Tools | `app/tools/{queries,constraints,actions}.py` | Deterministic reads, math, writes |
| Model access | `app/llm/provider.py` | Chat + availability probe, OpenAI or stub |
| Data | `app/db/{models,session,seed}.py` | ORM, engine, seed |

`policy.py` and `constraints.py` are pure (no I/O) and carry most of the test weight.

## Agent state machine (LangGraph)

```
START → ingest → agent_reason → guardrail
  agent_reason = LLM investigates via tool calls, proposes a decision
  guardrail    = deterministic recompute + validate/override the proposal
guardrail ──(reject | investigate)───────────→ finalize
guardrail ──(escalate)───────────────────────→ escalate → finalize
guardrail ──(accept | modify | source_alternate | confirm_existing)──→ approval_gate → act
act → validate
validate ──(acceptable)──────────────────────→ finalize
validate ──(discrepancy, iters remain)───────→ replan → agent_reason   ← the feedback loop
validate ──(discrepancy, no iters)───────────→ escalate → finalize
```

- Compiled with a `MemorySaver` checkpointer and `interrupt_before=["act"]`.
- `runner.py` resumes past `act` for low-risk actions; when `needs_human` is set it stops at
  the interrupt and returns `awaiting_approval`. The approval endpoint updates state + resumes.
- `agent_reason` runs the OpenAI function-calling loop when a key is usable, else a
  deterministic planner (which produces the guardrail baseline).

### Scenario 2 — two-phase loop

Phase is derived from state: `verify_existing` (no feedback yet) → `cover_gap` (after a
shortfall).

1. `verify_existing`: decision `confirm_existing`, expecting the full 500.
2. `act`: `simulate_vendor_response` → only 250 confirmed.
3. `validate`: expected 500 vs 250; inventory doesn't cover the gap → `feedback{gap: 250}`.
4. `replan` → `agent_reason` (`cover_gap`): re-reason, evaluate the alternate vendor for 250.
5. `guardrail` → `source_alternate` → `act` creates the alternate PO → `validate` passes.

## Data model

`products`, `inventory`, `client_orders` (demand signal), `vendors`, `vendor_products`
(terms), `vendor_purchase_orders`, `budgets`, `reorder_logs` (agent trace + result). Demand
is computed from `client_orders` (last-7-day rate projected over 30 days; >50% week-over-week
change ⇒ anomaly ⇒ investigate). Seed values are chosen so each SKU lands on a different
decision branch — see comments in `seed.py`.

## Request lifecycle

```
POST /runs {scenario, situation}
  → runner.start_run: new run_id, graph.invoke → ingest → agent_reason → guardrail
  → routes to act (pauses if HITL) or a terminal node
  → runner auto-resumes low-risk act→validate→…; stops at HITL if needed
  → persist ReorderLog; return full public state (decision, validation, trace, …)

POST /runs/{id}/approve {approved, edited_qty}
  → graph.update_state(approval); resume through act→validate→…; persist; return
```

## Extensibility

The same tool-using, validate-and-replan architecture generalizes to the assignment's
optional problems: replenishment (run S1 across many SKUs on a schedule), safety-stock tuning
(policy input), vendor reliability (already a routing signal), alternate sourcing (already in
S2), and demand-change detection (already the anomaly gate → Scenario 3).
```
