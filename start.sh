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
if ! "$VENV_DIR/bin/python" -c 'import fastapi, torch, torchvision, sklearn' >/dev/null 2>&1; then
  echo "Installing backend dependencies (first run may take a few minutes)..."
  "$VENV_DIR/bin/python" -m pip install -r "$BACKEND_DIR/requirements.txt"
fi

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

api_is_running() {
  curl -fsS --max-time 2 http://127.0.0.1:8001/api/health 2>/dev/null | grep -q '"ok":true'
}
web_is_running() {
  curl -fsS --max-time 2 http://127.0.0.1:5173/ 2>/dev/null | grep -q '<title>LoopLab'
}
port_is_busy() {
  command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

echo "Starting LoopLab..."
if api_is_running; then
  echo "API already running on port 8001."
else
  if port_is_busy 8001; then
    echo "Port 8001 is in use by another app. Stop it or change LoopLab's API port."
    exit 1
  fi
  (cd "$BACKEND_DIR" && exec "$VENV_DIR/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload) &
  API_PID=$!
fi

if web_is_running; then
  echo "Dashboard already running on port 5173."
else
  if port_is_busy 5173; then
    echo "Port 5173 is in use by another app. Stop it or use another dashboard port."
    exit 1
  fi
  (cd "$FRONTEND_DIR" && exec npm run dev -- --host 127.0.0.1 --strictPort) &
  WEB_PID=$!
fi

echo ""
echo "LoopLab dashboard: http://localhost:5173"
echo "API documentation: http://localhost:8001/docs"
if [ -n "$API_PID$WEB_PID" ]; then
  echo "Press Ctrl+C to stop services started by this command."
  wait
else
  echo "Both services were already running. Leave their original terminals open while using LoopLab."
fi
