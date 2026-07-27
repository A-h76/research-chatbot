# ✦ Soro (Personal AI / ResearchOS)

Private research & thesis writing assistant — ChatGPT-style chat grounded in
your uploads, plus a Paper Workspace, Discover, and citation tools.

Your OpenAI API key stays on the backend — never exposed to the browser.

Premium SPA frontend built with **React + TypeScript + Tailwind + shadcn/ui +
Framer Motion** (in `frontend/`), served by the Flask backend.

**Branding:** The SPA primarily brands as **Soro**. Some login/legal copy still
says Personal AI; CI/docs may say ResearchOS — same application.

**Features:** Google / magic-link login · streaming replies (Responses API) ·
live model dropdown · Projects (own instructions + memory) · selective
long-term memory · per-chat memory toggle · temperature & reasoning-effort
controls · auto chat titles · web search with sources · Postgres history ·
PDF/Word/image/text uploads · vision · RAG over your library · **Phase 1
structured paper analysis** + LLM overview · Paper Workspace (Structure /
Classification / Entities / Evidence / Graph / **Related**) · **Discover**
(OpenAlex) with Add to Library · **Crossref** metadata enrichment on upload ·
citation manager with BibTeX · writing / compare / gaps · ⌘K command palette ·
light/dark theme · fully responsive.

**Using the product:**
- **Library** → upload papers (preferred), or **Search → Discover → Add to
  Library** for metadata-only stubs (upload a PDF later for analysis/RAG)
- Open a paper for the Paper Workspace tabs (including Related)
- Ask Soro from the sidebar **More** menu or ⌘K; chat ＋ still attaches files
- Citations / Personalization / Settings from the avatar menu or toolbars

For the full engineering inventory, see [`PROJECT_STATUS.md`](PROJECT_STATUS.md).

---

## Quick start

The UI is a React + TypeScript app (in `frontend/`) that Flask serves as static
files in production. Build it once, then run the server:

```bash
pip install -r requirements.txt

# build the frontend (needs Node 18+)
cd frontend
npm install
npm run build
cd ..

# fill in .env (see below)
python server.py
# → open http://localhost:5000
```

For the research pipeline (Crossref enrich → Phase 1 → paper analysis) you also
need a **Postgres** `DATABASE_URL` and a worker:

```bash
python run_migrations.py   # after server has created core tables once
python worker.py
```

SQLite is fine for API-only local play; the worker needs Postgres
(`FOR UPDATE SKIP LOCKED`).

### Developing the frontend (hot reload)

Run three terminals for the full loop — Flask, worker, Vite:

```bash
# terminal 1 — backend
python server.py            # http://localhost:5000

# terminal 2 — worker (Postgres required)
python worker.py

# terminal 3 — frontend (proxies /api, /auth, /login to :5000)
cd frontend && npm run dev  # open http://localhost:5173
```

Vite proxies API/auth calls to Flask, so log in and everything works at
`:5173` while you edit. When you're done, `npm run build` and use `:5000`.

---

## Setting up `.env` (one time)

Copy `.env.example` and fill in the sections below.

### 1. OpenAI API key (required)
Paste your key into `OPENAI_API_KEY=` in `.env`.

### 2. Neon Postgres — free (recommended for worker / production)
1. Go to https://neon.tech → sign up (can use your Google account)
2. Create a project (any name, region close to you)
3. On the dashboard, click **Connect** → copy the connection string
   (looks like `postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`)
4. Paste it into `DATABASE_URL=` in `.env`

> Leave `DATABASE_URL` empty to test with a local SQLite file first — chat and
> most APIs work; switch to Neon (or any Postgres) before relying on the worker
> / Phase 1 pipeline.

### 3. Google login — free (~5 min)
1. Go to https://console.cloud.google.com → create a project (e.g. "Soro")
2. **APIs & Services → OAuth consent screen**
   - User type: **External** → fill app name, your email → save
3. **APIs & Services → Credentials → Create credentials → OAuth client ID**
   - Application type: **Web application**
   - Authorized redirect URIs — add BOTH:
     - `http://localhost:5000/auth/callback`
     - `http://127.0.0.1:5000/auth/callback`
     - (when you deploy later, also add `https://YOUR-DOMAIN/auth/callback`)
4. Copy the **Client ID** and **Client secret** into `.env`
5. While the consent screen is in "Testing" mode, add your Gmail under
   **Test users** (or click "Publish app" to allow any Google account)

Magic-link login also works (Resend or console fallback) without Google.

### 4. Who can log in
- `ALLOWED_EMAILS=` empty → **any Google account** may sign in
- To lock it down: `ALLOWED_EMAILS=you@example.com`

⚠️ With open login + public deployment, anyone can chat **on your API credit**.
Consider the whitelist if you deploy publicly.

### 5. `FLASK_SECRET_KEY`
Set any long random string (e.g. run
`python -c "import secrets;print(secrets.token_hex(32))"`).

### 6. Scholarly providers (optional but recommended)

| Variable | Purpose |
|----------|---------|
| `CROSSREF_MAILTO` | Polite pool identity for Crossref (recommended) |
| `CROSSREF_PLUS_TOKEN` | Crossref Plus (optional) |
| `OPENALEX_BASE_URL` | Defaults to public OpenAlex API (no key required) |
| `SEMANTIC_SCHOLAR_API_KEY` | Enables **Related** papers; without it Related stays empty |
| `ENABLE_CROSSREF` / `ENABLE_OPENALEX` / `ENABLE_SEMANTIC_SCHOLAR` | Ops kill-switches (default on) |

Crossref enrichment runs in the **worker** after text extract and **before**
Phase 1. Failures are soft — uploads still succeed.

### 7. Paper Chat Stage 1 (optional)
`PAPER_CHAT_PIPELINE_ENABLED=false` (default) | `shadow` | `true`

---

## How the model dropdown works

On load, the server calls OpenAI `/v1/models` **with your key** and lists every
chat-capable model your account has (gpt-5.x, gpt-4o, o-series, codex, …).
Non-chat models (whisper, tts, embeddings, sora, image, realtime, audio) are
excluded. The list refreshes automatically every 10 minutes. The picker lives
in the chat composer, next to ＋.

---

## File uploads, vision & RAG

- Upload from **Library** (preferred) or the chat ＋ button: PDF, DOCX,
  TXT/MD/CSV, PNG/JPG/GIF/WebP (session upload max ~25 MB; JWT path may differ)
- Worker path: extract → chunk/embed (`text-embedding-3-small`) → **Crossref**
  (DOI) → **Phase 1.1–1.7** → LLM paper overview
- Chat retrieves the most relevant sections from files in the current
  chat/project; JWT `/api/rag` is also available
- Images go to the model as vision input — use a vision-capable model
- Discover **Add to Library** stores **metadata only** (no third-party PDF
  fetch); upload a PDF later for analysis/RAG
- Library shows a **Metadata only** badge on Discover stubs

---

## Paper Workspace & Discover

- **Paper tabs:** Overview · Structure · Classification · Entities · Evidence ·
  Graph · Narrative · **Related** · Chat
- **Search page:** My Library corpus search + **Discover** (OpenAlex keyword
  search → Add to Library)
- Ops: `GET /api/worker/health`, `GET /api/health/providers`

---

## Citation manager

Avatar → **Citations**: add references manually, copy BibTeX per entry, or
export all as `references.bib`. The bot can save citations itself — say
"save this paper to my citations". Crossref-backed formatting is also available
via `GET /api/files/<id>/citation?style=`.

---

## Memory & Personalization

The bot selectively remembers durable facts (thesis topic, citation style,
tools, tone) and ignores one-off requests. Avatar → **Personalization** to set
global custom instructions and view/delete memories. Project memories are
scoped to their project.

---

## Projects

Sidebar → **Projects → ＋**. Each project has an emoji, name, and custom
instructions injected into chats in that project. Click a project to filter its
chats; use a chat's **⋯** menu to move it between projects.

---

## Deploying

**Docker / Railway:** multi-stage `Dockerfile` + `entrypoint.sh` (Gunicorn on
`0.0.0.0:$PORT`). Run a **separate worker** service (`python worker.py`) with
the same image/env. Apply migrations (`run_migrations.py`) against Postgres.

**Classic (Render / Fly / etc.):**
- build the frontend: `cd frontend && npm install && npm run build`
  (Flask serves `frontend/dist`)
- set the same `.env` vars on the host
- add `https://YOUR-DOMAIN/auth/callback` to Google OAuth redirect URIs
- web: `gunicorn -w 2 -k gthread --threads 8 -b 0.0.0.0:$PORT server:app`
- also run `python worker.py` (and Postgres) for the research pipeline

systemd units live under `deploy/systemd/`. `robots.txt` allows crawlers.

---

## Tests & lint

```bash
pytest
flake8 .
cd frontend && npm test && npm run lint
```

CI (`.github/workflows/ci.yml`) runs flake8 + pytest against Postgres + Redis.

---

## Notes

- UI is *inspired by* ChatGPT but branded **Soro / Personal AI** — don't
  present it as official ChatGPT if made public.
- "Training": the model itself can't be retrained via API; memory + library +
  Phase 1 provide the practical equivalent (persistent, personalized context).
- Architecture constraints: `docs/00-constitution.md`, `PROJECT_STATUS.md`.
