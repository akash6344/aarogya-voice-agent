#!/usr/bin/env bash
# Create/recreate the agent virtualenv and install dependencies.
set -euo pipefail
cd "$(dirname "$0")"

if [[ -x .venv/bin/python ]]; then
  if ! .venv/bin/python -c "import sys; sys.exit(0)" 2>/dev/null; then
    echo "Removing broken .venv (stale interpreter path)..."
    rm -rf .venv
  fi
fi

if [[ ! -x .venv/bin/python ]]; then
  echo "Creating agent/.venv..."
  python3 -m venv .venv
fi

.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e ".[test]"
echo "Agent ready. Run: .venv/bin/python scripts/init_db.py && ./dev.sh dev"
