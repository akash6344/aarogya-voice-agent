#!/usr/bin/env bash
# Start the LiveKit voice agent (NOT uvicorn — this is a worker, not a REST API).
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -x .venv/bin/python ]]; then
  echo "Missing agent/.venv — run:"
  echo "  python3 -m venv .venv && .venv/bin/pip install -e ."
  exit 1
fi

exec .venv/bin/python main.py "$@"
