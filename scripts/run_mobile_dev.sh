#!/usr/bin/env bash
# WSL-only fallback when Node is not installed on Windows.
# Requires: sudo apt install python3-venv python3-pip

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV="$HOME/.venvs/garmin-stats"
API_PID=""

cleanup() {
  if [[ -n "$API_PID" ]] && kill -0 "$API_PID" 2>/dev/null; then
    kill "$API_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if ! python3 -m venv --help >/dev/null 2>&1; then
  echo "Missing python3-venv. Run: sudo apt install python3-venv python3-pip" >&2
  exit 1
fi

if [[ ! -f "$VENV/bin/activate" ]]; then
  echo "Creating Python venv in $VENV ..."
  rm -rf "$VENV"
  mkdir -p "$(dirname "$VENV")"
  python3 -m venv "$VENV"
fi

if [[ ! -f "$VENV/bin/activate" ]]; then
  echo "venv is incomplete (no bin/activate). Run: sudo apt install python3-venv python3-pip" >&2
  exit 1
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

if ! python -c "import fastapi" >/dev/null 2>&1; then
  echo "Installing Python dependencies (first run only) ..."
  pip install -q -r requirements.txt
fi

if curl -sf --max-time 2 "http://127.0.0.1:8000/api/health" >/dev/null; then
  echo "FastAPI already running on http://127.0.0.1:8000"
else
  echo "Starting FastAPI on http://127.0.0.1:8000 ..."
  uvicorn api.main:app --reload --host 127.0.0.1 --port 8000 &
  API_PID=$!

  for _ in $(seq 1 60); do
    if curl -sf --max-time 2 "http://127.0.0.1:8000/api/health" >/dev/null; then
      break
    fi
    sleep 0.5
  done

  if ! curl -sf --max-time 2 "http://127.0.0.1:8000/api/health" >/dev/null; then
    echo "FastAPI did not become ready on http://127.0.0.1:8000/api/health" >&2
    exit 1
  fi
fi

echo "Starting Vite on http://127.0.0.1:5173 ..."
cd "$ROOT/frontend"
npm run dev
