# Architecture

This document goes one level deeper than the README: the component boundaries, the agent
state machine, the data model, and the request lifecycle.

## Design goals

1. **Reliable decisions.** The LLM drives the reasoning and proposes the decision, but it
   must not be able to invent numbers or take an action the business rules forbid. →
   deterministic tools own all math and a guardrail validates and can override the LLM.
2. **Genuine feedback loop.** The agent must detect when an action's *actual* outcome differs
   from what it expected and recover. → post-action validation re-reads persisted state and
   can loop back to re-plan.
3. **Runs anywhere.** Fully functional with no API key and no external infra. → stub LLM +
   SQLite fallback; Postgres/pgvector for the real deployment.

## Component boundaries

| Layer | Module | Responsibility | Depends on |
|---|---|---|---|
| API | `app/api/routes.py`, `app/main.py` | REST surface, request validation, CORS | runner, eval, db |
| Orchestration | `app/agent/graph.py`, `nodes.py`, `runner.py` | LangGraph state machine + HITL drive | tools, rag, llm, policy |
| LLM tool schema | `app/agent/tools_schema.py` | Function specs + dispatch + `assess_purchase` | tools |
| Decision policy | `app/agent/policy.py` | Pure map: analysis → decision (guardrail baseline) | (none) |
| Tools | `app/tools/{queries,constraints,actions}.py` | Deterministic reads, math, writes | db |
| Knowledge | `app/rag/{store,seed_rules}.py` | SOP retrieval (pgvector / cosine) | db, llm embeddings |
| Model access | `app/llm/provider.py` | Chat + embeddings, OpenAI or stub | config |
| Data | `app/db/{models,session,seed}.py` | ORM, engine, seed | (none) |

Each unit can be understood and tested in isolation. `policy.py` and `constraints.py` are
pure and have no I/O, so they carry most of the test weight.

## Agent state machine (LangGraph)

Nodes and transitions (`app/agent/graph.py`):

```
START → ingest → agent_reason → guardrail
  agent_reason = LLM investigates via tool calls, proposes a decision
  guardrail    = deterministic recompute + validate/override the proposal
guardrail ──(reject | investigate)───────────→ finalize
guardrail ──(escalate)───────────────────────→ escalate → finalize
guardrail ──(accept | modify | source_alternate | confirm_existing)──→ approval_gate → act
act → validate
validate ──(acceptable)──────────────────────→ finalize
validate ──(discrepancy, iters remain)───────→ replan → agent_reason  ← the feedback loop
validate ──(discrepancy, no iters)───────────→ escalate → finalize
```

`agent_reason` runs the OpenAI function-calling loop when a key is present, and a
deterministic planner (producing the guardrail baseline) otherwise.

- The graph is compiled with a `MemorySaver` checkpointer and `interrupt_before=["act"]`.
- `runner.py` invokes the graph, then repeatedly resumes past `act` for low-risk actions;
  when `needs_human` is set it stops at the interrupt and returns `awaiting_approval`. The
  approval endpoint updates the checkpointed state and resumes.

### Scenario 2 as a two-phase loop

Scenario 2 is where the loop is visible. Phase is derived from state:
`verify_existing` (no feedback yet) → `cover_gap` (after a shortfall).

1. `verify_existing`: decision = `confirm_existing`, expecting the full 500.
2. `act`: asks the supplier to confirm → only 250 confirmed (driven by
   `simulate_supplier_response` and the supplier's seeded `available_capacity`).
3. `validate`: expected 500 vs confirmed 250; inventory doesn't cover the gap → emits
   `feedback{gap: 250}`.
4. `replan` → `agent_reason`/`guardrail` (now `cover_gap`): the agent re-reasons with the
   shortfall feedback and evaluates the alternate supplier for exactly 250.
5. `decide` = `source_alternate` → `act` creates the alternate PO → `validate` passes → done.

## Data model

Mock supply-chain domain seeded in `app/db/seed.py`:

- `products` — sku, category, unit_cost, unit_volume, perishable, shelf_life
- `fulfillment_nodes` — node_id, region
- `inventory` — on_hand, reserved, safety_stock (per sku+node)
- `demand_forecast` — daily_forecast, horizon_days, recent_daily_actuals (for the
  reliability check)
- `suppliers` / `supplier_skus` — reliability, lead_time, min_order_qty, unit_price,
  available_capacity, is_primary
- `purchase_orders` — qty, confirmed_qty, status (open/confirmed/partial/…), unit_price
- `budgets` — allocated, spent (per node+category)
- `storage` — total_capacity_units, used_units (per node)
- `business_rules` — SOP text + embedding (pgvector on Postgres, JSON on SQLite)
- `agent_runs` — persisted trace + result per run (observability)

The seed values are deliberately chosen so each SKU lands on a different decision branch;
see the comments in `seed.py` for the arithmetic.

## Request lifecycle

```
POST /runs {scenario, situation}
  → runner.start_run: new run_id, graph.invoke(initial)
  → graph runs ingest → agent_reason → guardrail; routes to act (pauses) or a terminal node
  → runner auto-resumes low-risk act→validate→…; stops at HITL if needed
  → persist AgentRun; return full public state (decision, validation, trace, …)

POST /runs/{id}/approve {approved, edited_qty}
  → graph.update_state(approval) ; resume through act→validate→…
  → persist; return updated state
```

## Extensibility

The same tool-using, validate-and-replan architecture generalizes to the optional problems
in the brief: replenishment (run S1 across many SKUs on a schedule), safety-stock tuning
(policy input), supplier reliability (already a routing signal), and alternate sourcing
(already implemented for S2).
