# Diafragma

A camera-equipment rental platform with a voice AI attendant ("Nina"). Customers can ask by voice, phone call or Telegram: *"is there a camera free on Saturday?"*. The agent answers from real inventory data, then reserves and takes payment.

This is also a learning project: each phase below has a concrete "done when" goal.

## Architecture

- **API (FastAPI)**: the only component that touches the domain tables. Exposes the catalog, reservations, auth and the tools the agent calls.
- **Agent (Nina)**: LiveKit handles audio (STT → LLM → TTS, VAD, turn detection). The conversation logic is a LangGraph graph whose nodes call API tools. It has no data of its own. If a fact didn't come from an API tool, it doesn't know it.
- **Worker**: consumes SQS messages (Telegram audio, reservation expiry, payment webhooks). It runs the same LangGraph graph as the voice agent, so both channels share one set of business rules, and then sends the reply.
- **Postgres (RDS + pgvector)**: relational data, vector search for catalog RAG, and LangGraph checkpoints (conversation state) in a separate `agent` schema.
- **SQS + DLQ / EventBridge Scheduler**: everything that doesn't need to be in the real-time path.
- **S3**: audio and other files.

Synchronous path: channel → LiveKit → agent → API → database.
Asynchronous path: webhooks and schedules → SQS → worker.

## Stack

Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL 18 · pytest + testcontainers · ruff · uv.
Planned: LiveKit Agents, LangGraph, pgvector, SQS, EventBridge, ECS Fargate, GitHub Actions (OIDC), OpenTelemetry, LangSmith or Langfuse (agent traces and evals).

## Where LangGraph fits

LangGraph models the conversation as a state machine: typed state, nodes (functions or LLM calls) and edges (routing). It is introduced gradually, not on day one:

| Phase | LangGraph piece | Why |
|---|---|---|
| 2 | Not used yet | Start with LiveKit's plain function tools to get a latency baseline. |
| 3 | `interrupt()` before the booking node | "Always confirm before booking" becomes a graph rule, not a prompt instruction. |
| 5 | Router node + catalog / reservation / payment subgraphs, Pydantic state | Sub-agents with structured outputs. A node can be a plain function; only some need an LLM. |
| 5 | Postgres checkpointer (short-term) + store (long-term) | Conversation state survives restarts; past rentals are remembered per client. |
| 6 | Same graph run by the worker, one thread per Telegram chat | One source of business rules for voice and text channels. |
| 8 | Traces per node | See which node is slow or which tool fails. |

## Fintech concerns

Payments are where the project goes beyond a normal CRUD app:

- **Idempotency keys** on every request that creates a reservation or payment.
- **Webhook signature verification**, and processing each payment event exactly once. `Payment` already has a unique `(provider, external_id)`.
- **Money as integers in minor units** plus a currency code, never floats. Already done (`*_cents` columns).
- **Append-only payment records**: record refunds and chargebacks as new rows instead of editing old ones. Today `Payment.status` is updated in place (`refunded`); revisit this in Phase 6.
- **Reconciliation**: a scheduled job that compares the provider's records with ours and flags mismatches.
- **Audit trail**: who changed a reservation's status, when, and through which channel.

## Domain

- **User** is anyone who talks to the platform: admins (email + password) and customers, who may exist only as a phone number or Telegram chat id. Every user needs at least one contact. Reservations belong to a user.
- **Product** is the model ("Sony A7 III"); **Unit** is a physical item with a serial number. Reservations book units.
- **Reservation → ReservationItem → UnitBlock**: a `UnitBlock` holds a date range for one unit. A Postgres `EXCLUDE` constraint on `(unit_id, period &&)` makes double booking impossible at the database level, whatever the application does. Maintenance windows use the same table.
- Reservation status: `pending → confirmed → picked_up → returned`, or `cancelled` / `expired`. Pending reservations carry an `expires_at`.

## Getting started

```bash
uv sync --dev
cp .env.example .env            # needs POSTGRES_PASSWORD, DATABASE_URL, SECRET_KEY (>=32 chars)
docker compose up -d
uv run alembic upgrade head
uv run python seed_admin.py you@example.com "Your Name"
uv run python seed_products.py
uv run fastapi dev src/diafragma/main.py
```

Tests need Docker (they start a throwaway Postgres):

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run alembic check            # models must match migrations
```

## Roadmap

| Phase | Goal | Status |
|---|---|---|
| 0. Foundation | Repo layout, domain model, 30–50 fictional products | Done: 59 products, 2 stores and units seeded from `produtos.json` |
| 1. Concurrency | 20 simultaneous bookings of the same unit → exactly one wins | In progress: `EXCLUDE` constraint and race test on `UnitBlock` exist; reservation service/API and idempotency keys don't |
| 2. First voice agent | Ask by voice, get an answer from real data | Not started |
| 3. Sounding human | Interruptions, filler while tools run, numbers/dates spoken naturally, always confirm before booking | Not started |
| 4. RAG over catalog | "Does this lens fit my Canon R6?", measured with recall@k and faithfulness (vector → hybrid → rerank) | Not started |
| 5. Sub-agents and memory | LangGraph subgraphs returning schema-validated JSON; remembers past rentals | Not started |
| 6. Async | Telegram audio via SQS + worker, auto-expiring reservations, signed payment webhook, reconciliation | Not started |
| 7. Intent classifier | Fine-tuned small model vs base vs large LLM (F1, JSON validity, latency, cost) | Not started |
| 8. AWS + CI/CD + observability | Push to main → tests, evals, image, deploy; latency per STT/LLM/TTS | CI (lint, tests, migrations) done |

Auth (JWT, admin/customer roles) and product CRUD are done.

### Pitfalls to remember

- **Phase 0:** start with the domain, not the LLM.
- **Phase 1:** never check availability and insert in two steps. Let the constraint decide.
- **Phase 2:** if it didn't come from a tool, the agent doesn't know it. Keep answers short for voice, and track time-to-first-audio from day one.
- **Phase 3:** turning numbers into spoken text is deterministic code, not prompting.
- **Phase 4:** never evaluate RAG by eye. Keep ~40 questions with expected answers.
- **Phase 5:** a sub-agent that doesn't justify itself should be a plain function (in LangGraph, a node without an LLM). Compare the graph's latency against the Phase 2 baseline, because every extra LLM hop is time the caller spends waiting in silence.
- **Phase 6:** SQS delivers at least once, so consumers must be idempotent. The same applies to payment webhooks.
- **Phase 7:** keep test examples out of training data.
- **Phase 8:** the voice agent is long-lived, so it belongs on Fargate, not Lambda.
