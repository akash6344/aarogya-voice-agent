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

## Deploy (LiveKit Cloud)

The agent is a **LiveKit worker**, not a REST API. Host it on **LiveKit Cloud** (assignment stack), not Vercel/Railway.

### 1. Install LiveKit CLI

```bash
brew install livekit-cli
# or: curl -sSL https://get.livekit.io/cli | bash
lk cloud auth
```

### 2. Create the cloud agent (from `agent/`)

```bash
cd agent
lk agent create
```

This links the folder to your LiveKit project and creates `livekit.toml`. Commit that file and push to GitHub.

### 3. Set secrets (copy from local `agent/.env`)

```bash
lk agent secrets set --from-file .env
```

Or set in [cloud.livekit.io](https://cloud.livekit.io) → **Agents** → your agent → **Secrets**.

**Required:**

| Secret | Notes |
|--------|--------|
| `LIVEKIT_URL` | Same as Vercel web |
| `LIVEKIT_API_KEY` | Same as Vercel web |
| `LIVEKIT_API_SECRET` | Same as Vercel web |
| `DATABASE_URL` | Neon Postgres |
| `DEEPGRAM_API_KEY` | STT |
| `SARVAM_API_KEY` | STT + Telugu TTS |
| `ELEVEN_API_KEY` | TTS EN/HI |
| `GEMINI_API_KEY` | LLM (required in cloud) |
| `LLM_PROVIDER` | Use **`gemini`** or **`auto`** (Ollama is not available in cloud) |
| `GEMINI_MODEL` | e.g. `gemini-2.0-flash-001` |
| `ELEVEN_TTS_MODEL` | `eleven_flash_v2_5` |
| `ELEVEN_VOICE_ID` | premade voice ID |
| `ELEVEN_VOICE_ID_EN` / `ELEVEN_VOICE_ID_HI` | same premade voice |
| `SARVAM_TTS_MODEL` | `bulbul:v2` |
| `SARVAM_TTS_SPEAKER` | `anushka` |
| `CLINIC_TIMEZONE` | `Asia/Kolkata` |

### 4. Deploy

```bash
cd agent
lk agent deploy
```

Or connect GitHub in LiveKit dashboard and deploy from the `agent/` directory.

### 5. Database

Run once against Neon (from your laptop):

```bash
cd agent && .venv/bin/python scripts/init_db.py
```

### Full stack after deploy

| Piece | Host |
|-------|------|
| Web UI + token API | Vercel (`web/`) |
| Voice agent | **LiveKit Cloud** (`agent/`) |
| Database | Neon |

Both web and agent must use the **same** `LIVEKIT_URL` / API key / secret.

## Test

```bash
cd agent && .venv/bin/python -m pytest
```
