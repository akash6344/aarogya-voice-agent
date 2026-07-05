# Web

Browser UI and the LiveKit **token API** (`/api/livekit-token`). This package does not
run STT, LLM, TTS, or touch the database.

## Owns

- `app/`, `components/`, `lib/`
- `package.json`, `node_modules/`, `.next/`
- `.env.local` — LiveKit credentials (same project as `agent/.env`) + rate-limit / Turnstile

Copy LiveKit keys from `agent/.env`:

```bash
cd web
cp .env.example .env.local
# then paste LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET from ../agent/.env
```

## Run locally

```bash
cd web
cp .env.example .env.local   # copy LIVEKIT_* from ../agent/.env
pnpm install
pnpm dev                       # http://localhost:3000
```

## Deploy

Point Vercel (or similar) at the **`web/`** directory as the project root. Set env vars
from `.env.example` in the hosting dashboard.
