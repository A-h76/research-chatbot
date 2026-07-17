# ✦ Personal AI

Private ChatGPT-style assistant for research & thesis writing.
Your OpenAI API key stays on the backend — never exposed to the browser.

Premium SPA frontend built with **React + TypeScript + Tailwind + shadcn/ui +
Framer Motion** (in `frontend/`), served by the Flask backend.

**Features:** Google login · streaming replies (Responses API) · live model
dropdown from your account · Projects (own instructions + memory) · selective
long-term memory (editable, importance-rated) · per-chat memory toggle ·
temperature & reasoning-effort controls · auto chat titles · web search with
sources · Postgres history · PDF/Word/image/text uploads · vision (send images
to vision models) · RAG over your documents (embeddings + retrieval) · citation
manager with BibTeX export (the bot can save citations itself) · custom
instructions · routed Projects/Files/Citations/Memory/Settings pages ·
collapsible context panel · light/dark theme · fully responsive.

**Using the new features:** attach files with the ＋ button in the chat box
(PDFs/Word docs are indexed for retrieval; images go to the model as vision
input). Your avatar → Files / Citations / Personalization / Settings.
Ask the bot things like "save this paper to my citations" — it has a
save_citation tool.

---

## Quick start

The UI is a React + TypeScript app (in `frontend/`) that Flask serves as static
files in production. Build it once, then run the server:

```bash
cd chatbot
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

### Developing the frontend (hot reload)

Run two terminals — Flask for the API, Vite for the UI with instant reload:

```bash
# terminal 1 — backend
python server.py            # http://localhost:5000

# terminal 2 — frontend dev server (proxies /api, /auth, /login to :5000)
cd frontend && npm run dev  # open http://localhost:5173
```

Vite proxies API/auth calls to Flask, so log in and everything works at
`:5173` while you edit. When you're done, `npm run build` and use `:5000`.

---

## Setting up `.env` (one time)

### 1. OpenAI API key (required)
Paste your key into `OPENAI_API_KEY=` in `.env`.

### 2. Neon Postgres — free (recommended)
1. Go to https://neon.tech → sign up (can use your Google account)
2. Create a project (any name, region close to you)
3. On the dashboard, click **Connect** → copy the connection string
   (looks like `postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`)
4. Paste it into `DATABASE_URL=` in `.env`

> Leave `DATABASE_URL` empty to test with a local SQLite file first — everything works, you can switch to Neon later.

### 3. Google login — free (~5 min)
1. Go to https://console.cloud.google.com → create a project (e.g. "Personal AI")
2. **APIs & Services → OAuth consent screen**
   - User type: **External** → fill app name "Personal AI", your email → save
3. **APIs & Services → Credentials → Create credentials → OAuth client ID**
   - Application type: **Web application**
   - Authorized redirect URIs — add BOTH:
     - `http://localhost:5000/auth/callback`
     - `http://127.0.0.1:5000/auth/callback`
     - (when you deploy later, also add `https://YOUR-DOMAIN/auth/callback`)
4. Copy the **Client ID** and **Client secret** into `.env`
5. While the consent screen is in "Testing" mode, add your Gmail under
   **Test users** (or click "Publish app" to allow any Google account)

### 4. Who can log in
- `ALLOWED_EMAILS=` empty → **any Google account** may sign in (current setting)
- To lock it down: `ALLOWED_EMAILS=ahmhasan045@gmail.com`

⚠️ With open login + public deployment, anyone can chat **on your API credit**. Consider the whitelist if you deploy publicly.

### 5. FLASK_SECRET_KEY
Set any long random string (e.g. run `python -c "import secrets;print(secrets.token_hex(32))"`).

---

## How the model dropdown works

On load, the server calls OpenAI `/v1/models` **with your key** and lists every
chat-capable model your account has (gpt-5.6-sol/terra/luna, gpt-5.5, gpt-5.x,
gpt-4o, o3, o4-mini, codex models...). Non-chat models (whisper, tts,
embeddings, sora, image, realtime, audio) are excluded because they can't chat.
The list refreshes automatically every 10 minutes — no code changes ever needed
when OpenAI ships new models. The picker lives in the chat box, next to ＋.

## File uploads, vision & RAG

- **＋ button** in the chat box: PDF, DOCX, TXT/MD/CSV, PNG/JPG/GIF/WebP (max 25 MB)
- Documents are extracted, split into sections, and embedded
  (`text-embedding-3-small`); every question retrieves the most relevant
  sections from files in the current chat/project automatically
- Images are sent to the model as vision input — use a vision-capable model
  (gpt-4o, gpt-5.x)
- Manage everything under **your avatar → Files**

## Citation manager

Avatar → **Citations**: add references manually, copy BibTeX per entry, or
export all as `references.bib`. The bot can save citations itself — say
"save this paper to my citations".

## Memory & Personalization

The bot selectively remembers durable facts (thesis topic, citation style,
tools, tone) and ignores one-off requests. Avatar → **Personalization** to set
global custom instructions and view/delete memories. Project memories are
scoped to their project.

## Projects

Sidebar → **Projects → ＋**. Each project has an emoji, name, and custom
instructions injected into every chat in that project. Click a project to
filter its chats; use a chat's **⋯ menu** to move it between projects.

## Deploying later (optional)

Works on Render/Railway/Fly as a standard Flask app:
- build the frontend first: `cd frontend && npm install && npm run build`
  (Flask serves the resulting `frontend/dist` — build it as part of your deploy step)
- set the same `.env` vars in the host's environment settings
- add `https://YOUR-DOMAIN/auth/callback` to Google OAuth redirect URIs
- run with `gunicorn -w 2 -k gthread --threads 8 -b 0.0.0.0:$PORT server:app`
  (add `gunicorn` to requirements)
- `robots.txt` already allows all search engine crawlers

## Notes

- UI is *inspired by* ChatGPT but branded "Personal AI" — don't present it as official ChatGPT if made public.
- "Training": the model itself can't be retrained via API; the memory system provides the practical equivalent (persistent, personalized context).
