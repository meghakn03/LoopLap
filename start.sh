#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/.venv"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install it from https://www.python.org/downloads/macos/ and run ./start.sh again."
  exit 1
fi
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Node.js and npm are required. Install the LTS version from https://nodejs.org/ and run ./start.sh again."
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating Python environment..."
  python3 -m venv "$VENV_DIR"
fi
echo "Installing backend dependencies (first run may take a few minutes)..."
"$VENV_DIR/bin/python" -m pip install -q --upgrade pip
"$VENV_DIR/bin/python" -m pip install -q -r "$BACKEND_DIR/requirements.txt"

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "Installing dashboard dependencies..."
  (cd "$FRONTEND_DIR" && npm install)
fi

API_PID=
WEB_PID=
cleanup() {
  trap - INT TERM EXIT
  [ -z "$API_PID" ] || kill "$API_PID" 2>/dev/null || true
  [ -z "$WEB_PID" ] || kill "$WEB_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "Starting LoopLab..."
(cd "$BACKEND_DIR" && "$VENV_DIR/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload) &
API_PID=$!
(cd "$FRONTEND_DIR" && npm run dev -- --host 127.0.0.1) &
WEB_PID=$!

echo ""
echo "LoopLab dashboard: http://localhost:5173"
echo "API documentation: http://localhost:8000/docs"
echo "Press Ctrl+C to stop both services."
wait
