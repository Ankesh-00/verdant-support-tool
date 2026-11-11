# Deployment notes

Any free tier works. One simple split that has been verified to work:

## Backend + database — Render
1. Create a **PostgreSQL** instance (Render → New → Postgres). Copy its
   *Internal/External Database URL*.
2. Create a **Web Service** from this repo, root directory `backend`:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
     (a `Procfile` with the same line is included).
   - Environment variables (from `backend/.env.example`):
     - `DATABASE_URL` — the Render Postgres URL. If it starts with
       `postgres://`, change it to `postgresql+psycopg2://`.
     - `WEBHOOK_SECRET=verdant-demo-secret-2026`
     - `JWT_SECRET` — any long random string
     - `GROQ_API_KEY` — your Groq key
     - `GROQ_MODEL=openai/gpt-oss-120b`
     - `SEED_AGENT_USERNAME`, `SEED_AGENT_PASSWORD`
     - `CORS_ORIGINS` — your deployed frontend URL (e.g. `https://xxx.vercel.app`)
3. Tables are created and the agent is seeded on first boot.
   Your webhook endpoint is `https://<service>.onrender.com/webhook`.

## Frontend — Vercel / Netlify
- Root directory `frontend`, framework **Vite**
  (build `npm run build`, output `dist`).
- Environment variable `VITE_API_URL` = your Render backend URL.

## Verify after deploy
```bash
WEBHOOK_SECRET=verdant-demo-secret-2026 \
  python backend/send_webhook.py "What is your return policy?" \
  --url https://<service>.onrender.com/webhook
```
Then open the frontend, go to Agent, sign in, and the message should be there.
