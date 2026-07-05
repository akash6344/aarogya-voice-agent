# Agent

Python **LiveKit voice worker** — joins rooms, runs the voice pipeline, and calls
scheduling tools against Postgres.

## Owns

- `main.py`, `clinic/` — agent logic, tools, providers, prompts
- `database/` — SQL schema + seed (used only by the agent)
- `scripts/` — migrations + env validation
- `tests/` — pytest unit tests
- `pyproject.toml`, `.venv/`
- `.env` — model API keys, `DATABASE_URL`, LiveKit worker credentials

## Run locally

**This is a LiveKit worker, not a FastAPI/uvicorn server.** Do not run `uvicorn main:app`.

**LLM:** defaults to **`auto`** — Gemini for best tool-calling quality, Ollama only when Gemini returns a rate-limit (429/quota). Set `LLM_PROVIDER=gemini` or `ollama` to force one provider. Ollama must be running for fallback (`ollama serve`).

Run from the **`agent/` folder** (not the repo root):

```bash
# if you are already inside agent/, use ../web for the web app
cd agent
cp .env.example .env           # fill in all keys
./setup.sh                     # or: python3 -m venv .venv && .venv/bin/pip install -e ".[test]"
.venv/bin/python scripts/init_db.py
.venv/bin/python main.py download-files   # first time only
./dev.sh dev                   # start the voice worker
```

Shortcut:

```bash
cd agent && chmod +x dev.sh && ./dev.sh dev
```

## Deploy

Deploy this folder to **LiveKit Build**. Set env vars from `.env.example` in the
LiveKit agent dashboard.

## Test

```bash
cd agent && .venv/bin/python -m pytest
```
