# Verdant & Co — Support Draft Tool

A small production-minded slice of an AI-assisted support tool. Customer messages
arrive by webhook (or the built-in Customer view), an LLM drafts a reply from the
brand's knowledge base, and a signed-in agent reviews, edits, and approves it.

**Stack:** React (Vite) · FastAPI · PostgreSQL (SQLAlchemy) · Groq (`openai/gpt-oss-120b`).

- **Deployed app:** `<add your frontend URL>`
- **Webhook endpoint:** `<backend URL>/webhook`
- **Agent login:** `agent` / `verdant123` (override with `SEED_AGENT_*`)

## Run locally

**1. Postgres** (via Docker, from repo root):
```bash
docker compose up -d        # Postgres on localhost:5432
```

**2. Backend:**
```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
# (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env         # then set GROQ_API_KEY
uvicorn app.main:app --reload --port 8000
```
Tables are created and the demo agent is seeded on first start.

**3. Frontend:**
```bash
cd frontend
cp .env.example .env         # VITE_API_URL defaults to http://localhost:8000
npm install
npm run dev                  # http://localhost:5173
```

**4. Send a webhook test** (correctly HMAC-signed):
```bash
cd backend
python send_webhook.py "What is your return policy?"
```

## How it works end to end
Open the Customer view → send a sample message → it hits the same service the
webhook uses (save customer + conversation + message, then draft). Switch to the
Agent view → sign in → the conversation is on top → edit the draft → **Approve**.
Switch back to Customer → the approved reply appears (drafts never do).

## Key decisions (and what I cut)
- **One service path for all inbound messages.** The Customer view and `/webhook`
  both call `process_incoming_message`, so they behave identically by construction.
- **Draft generation is best-effort and never fails the webhook.** If Groq errors,
  we store a `failed` draft with the error and a safe fallback; the agent still
  gets a usable box. The webhook always returns 2xx once the message is saved.
- **Whole knowledge base in the prompt, no retrieval.** It's ~150 words — retrieval
  would add latency and failure modes for no accuracy gain. *This stops working*
  once a brand's KB exceeds a few thousand tokens or we serve many brands; then
  I'd switch to per-brand embedding retrieval (pgvector).
- **Grounding over fluency.** The system prompt forbids inventing policies, order
  status, or medical advice, and tells the model to escalate when the KB doesn't
  cover the question ("Do you deliver to Dubai?", the allergy message).
- **HMAC on raw bytes + idempotency on `event_id`** so retried webhooks don't
  double-draft. IDs are string UUIDs so the schema runs on Postgres or SQLite.
- **Cut for time:** tests beyond manual, Alembic migrations (tables auto-create),
  draft regeneration button, pagination, and polished design.

## Where AI helped — and got something wrong
AI (Claude) scaffolded the FastAPI routers, the React components, and the SQLAlchemy
models quickly. **Where it got it wrong:** an early version verified the webhook
signature against the *parsed-then-reserialized* JSON body, which changes the bytes
(key order / spacing) and makes a valid HMAC fail intermittently. Fixed by reading
`await request.body()` and signing the raw bytes before parsing.

## Two questions
**1. A message fails at 2 a.m. — what does the agent see, and how do I debug it?**
The message is still saved and the conversation shows a draft marked **failed**
with a safe fallback ("one of our team will reply shortly") plus the error reason,
so the agent is never blocked — they just write the reply themselves. To diagnose,
I'd read the stored `drafts.error_detail` and the structured server logs (the
exception is logged with the message id); in production those logs go to the host's
log drain (Render/Railway) or an error tracker like Sentry.

**2. Serving 20 brands, each with its own KB and agents — what changes first?**
Make everything tenant-scoped. There's already a `brand_id` on customers,
conversations, and messages; I'd add a `brands` table and a per-brand `knowledge_base`
(row or document), scope every agent and query by `brand_id`, and route webhooks by
the payload's `brand_id`. The prompt would load that brand's KB instead of a hard-coded
one — which is also the point where I'd move from "whole KB in prompt" to per-brand
retrieval so each tenant's context stays small and isolated.
