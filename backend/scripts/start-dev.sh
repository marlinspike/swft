#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

if ! python -c "import swft" >/dev/null 2>&1; then
  pip install -e ..
fi

exec uvicorn app.main:app --reload --host 127.0.0.1 --port "${PORT:-8000}"
