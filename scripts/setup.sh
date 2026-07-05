#!/usr/bin/env bash
# Fresh install for web + agent after clone or path changes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Cleaning build artifacts (not for git)..."
rm -rf "$ROOT/agent/.pytest_cache" "$ROOT/agent/"*.egg-info
rm -rf "$ROOT/web/node_modules" "$ROOT/web/.next" "$ROOT/web/tsconfig.tsbuildinfo"
find "$ROOT/agent" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

echo "==> Syncing web/.env.local LiveKit keys from agent/.env..."
if [[ -f "$ROOT/agent/.env" ]]; then
  python3 - <<'PY' "$ROOT/agent/.env" "$ROOT/web/.env.local"
import sys
from pathlib import Path

agent_env = Path(sys.argv[1])
web_env = Path(sys.argv[2])
keys = {}
for line in agent_env.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    keys[k.strip()] = v.strip()

def get(name, default=""):
    return keys.get(name, default)

content = f"""# Web app only — token service + public endpoint protection.
# LiveKit keys synced from agent/.env (same LiveKit project).

LIVEKIT_URL={get('LIVEKIT_URL')}
LIVEKIT_API_KEY={get('LIVEKIT_API_KEY')}
LIVEKIT_API_SECRET={get('LIVEKIT_API_SECRET')}

ALLOWED_ORIGINS=http://localhost:3000
TURNSTILE_SECRET_KEY=
NEXT_PUBLIC_TURNSTILE_SITE_KEY=
MAX_CALLS_PER_IP_PER_HOUR=10
"""
web_env.write_text(content)
print(f"Wrote {web_env}")
PY
fi

echo "==> Agent: ensure venv + install..."
cd "$ROOT/agent"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e ".[test]"

echo "==> Agent: run tests..."
.venv/bin/python -m pytest -q

echo "==> Agent: init database (ORM)..."
.venv/bin/python scripts/init_db.py

echo "==> Agent: import smoke test..."
.venv/bin/python -c "import main; from clinic.orm.tables import Clinic; print('agent ok')"

echo "==> Web: install + typecheck + build..."
cd "$ROOT/web"
if command -v corepack >/dev/null 2>&1; then
  corepack enable >/dev/null 2>&1 || true
  corepack pnpm install
  corepack pnpm run typecheck
  corepack pnpm run build
else
  npm install
  npm run typecheck
  npm run build
fi

echo ""
echo "All checks passed. Start with:"
echo "  cd web && pnpm dev"
echo "  cd agent && ./dev.sh dev"
