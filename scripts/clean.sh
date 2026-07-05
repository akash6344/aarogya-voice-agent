#!/usr/bin/env bash
# Remove local build artifacts before git push / deploy. Safe to run anytime.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Removing build artifacts (not source code)..."
rm -rf \
  "$ROOT/web/node_modules" \
  "$ROOT/web/.next" \
  "$ROOT/web/.turbo" \
  "$ROOT/web/tsconfig.tsbuildinfo" \
  "$ROOT/web/out" \
  "$ROOT/agent/.venv" \
  "$ROOT/agent/.pytest_cache" \
  "$ROOT/agent/"*.egg-info

find "$ROOT/agent" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

echo "Done. Secrets (.env, .env.local) are gitignored — verify with: git status"
