#!/usr/bin/env bash
# One-command runner for the Arbor reference implementation.
#
#   ./run.sh          set up, run the test suite, then the demo
#   ./run.sh demo     set up and run only the demo
#   ./run.sh test     set up and run only the test suite
#   ./run.sh api      set up and serve the API on http://127.0.0.1:8000
#
# "Set up" creates .venv and installs requirements.txt the first time, and is
# skipped on later runs unless requirements.txt has changed.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

MODE="${1:-all}"
case "$MODE" in
  all|demo|test|api) ;;
  *)
    echo "usage: ./run.sh [all|demo|test|api]" >&2
    exit 2
    ;;
esac

PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "error: $PYTHON not found. Install Python 3.12 or newer, or set PYTHON=/path/to/python." >&2
  exit 1
fi

VENV=".venv"
STAMP="$VENV/.requirements.sha256"

if [ ! -x "$VENV/bin/python" ]; then
  echo "==> Creating virtual environment in $VENV"
  "$PYTHON" -m venv "$VENV"
fi

WANT="$("$VENV/bin/python" -c 'import hashlib,sys; print(hashlib.sha256(open("requirements.txt","rb").read()).hexdigest())')"
if [ ! -f "$STAMP" ] || [ "$(cat "$STAMP")" != "$WANT" ]; then
  echo "==> Installing dependencies"
  "$VENV/bin/python" -m pip install --quiet --disable-pip-version-check -r requirements.txt
  echo "$WANT" > "$STAMP"
fi

# The seven package roots (same list as pytest.ini and scripts/run_demo.py).
export PYTHONPATH="backend/audit:backend/approval:backend/gateway:graph/ontology:graph/focal:memory:platform${PYTHONPATH:+:$PYTHONPATH}"

if [ "$MODE" = "all" ] || [ "$MODE" = "test" ]; then
  echo "==> Running the test suite"
  "$VENV/bin/python" -m pytest
fi

if [ "$MODE" = "all" ] || [ "$MODE" = "demo" ]; then
  echo "==> Running the demo mission"
  "$VENV/bin/python" scripts/run_demo.py
fi

if [ "$MODE" = "api" ]; then
  # The API has no authentication, so it listens on this machine only.
  echo "==> Serving the API on http://127.0.0.1:8000 (Ctrl+C to stop)"
  exec "$VENV/bin/python" -m uvicorn r2pip_platform.app:app --host 127.0.0.1 --port 8000
fi
