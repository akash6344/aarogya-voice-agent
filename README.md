# Aarogya — AI Voice Medical Appointment Assistant

Voice-first clinic scheduling: book, reschedule, cancel, and ask about appointments by
speaking. Built on **LiveKit Agents** with a **Next.js** browser client.

Supports **English, Hindi, and Telugu**, with user-selectable STT (Deepgram / Sarvam /
ElevenLabs).

---

## Repository layout

Each side is a **self-contained package** with its own dependencies, env file, and README.

```
voice_llm_agent/
├── web/                 Browser UI + LiveKit token API  → deploy to Vercel
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── package.json
│   ├── .env.local       (gitignored — copy from .env.example)
│   └── README.md
│
├── agent/               Python voice worker + scheduling  → deploy to LiveKit Build
│   ├── main.py
│   ├── clinic/
│   ├── database/        SQL schema + seed (agent-only)
│   ├── scripts/         migrations + env validation
│   ├── pyproject.toml
│   ├── .env             (gitignored — copy from .env.example)
│   └── README.md
│
└── README.md            (this file)
```

**There is no shared root `.env`.** Each package loads only its own config.

| Concern | `web/` | `agent/` |
|---------|--------|----------|
| UI, language + STT picker | ✅ | |
| Issue LiveKit tokens | ✅ | |
| Voice conversation (STT/LLM/TTS) | | ✅ |
| Appointment tools + Postgres | | ✅ |
| `node_modules` / `.venv` | ✅ | ✅ |
| Env file | `.env.local` | `.env` |

They connect through **LiveKit Cloud** (WebRTC audio), not direct HTTP between apps.

---

## Quick start

One-shot fresh install (recreates deps, runs tests, builds web):

```bash
./scripts/setup.sh
```

**Terminal 1 — web** (from repo root `aarogya-voice-agent/`)

```bash
cd web
cp .env.example .env.local    # LiveKit URL + API key/secret
pnpm install && pnpm dev
```

**Terminal 2 — agent**

```bash
cd agent
./dev.sh dev
```

If you are already inside `agent/`, start web with `cd ../web && pnpm dev`.

Open http://localhost:3000, pick language + STT, start talking.

Validate all external services:

```bash
cd agent && .venv/bin/python scripts/validate_env.py
```

---

## Voice loop

```
Browser (web)  →  token  →  LiveKit room  ←  agent worker
                              ↑ WebRTC audio
agent: VAD → STT → Gemini + tools → TTS → playback (barge-in supported)
```

## Deployment

| Package | Host | Root directory |
|---------|------|----------------|
| `web/` | Vercel | `web` |
| `agent/` | LiveKit Build | `agent` |
| Database | Neon | run `agent/scripts/init_db.py` |

Set env vars in each host from that package's `.env.example`.

## Docs per package

- [web/README.md](web/README.md) — UI + token route
- [agent/README.md](agent/README.md) — voice worker + tools
- [agent/database/README.md](agent/database/README.md) — schema + migrations

## Demo checklist (Loom)

Voice booking · continuous call-like conversation · doctor selection by voice · VAD ·
turn detection · noise cancellation · barge-in · spoken confirmation · architecture
explanation.
