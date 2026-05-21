#!/usr/bin/env bash
# [Section: strict mode]
# Fail fast on errors, undefined vars, and failed pipes to avoid partial setup.
set -euo pipefail

# [Section: project paths]
# Resolve project root relative to this script and define the venv location.
# This mirrors the production script exactly.
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

# [Section: port helpers]
# Detect an already-running local app in the expected port range,
# and choose a free launch port when starting a new server.
find_running_port() {
  local port
  for port in $(seq 5006 5020); do
    if lsof -i TCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "$port"
      return 0
    fi
  done
  return 1
}

find_open_port() {
  local port
  port=5006
  while lsof -i TCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; do
    port=$((port + 1))
  done
  echo "$port"
}

# [Section: choose python interpreter]
# Prefer existing venv python; otherwise create a venv with python3.11 or python3.
if [[ -x "$VENV_DIR/bin/python" ]]; then
  PYTHON_BIN="$VENV_DIR/bin/python"
else
  if command -v python3.11 >/dev/null 2>&1; then
    PYTHON_CMD="python3.11"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
  else
    echo "Error: python3.11 or python3 is required but was not found."
    exit 1
  fi

  echo "Creating virtual environment at $VENV_DIR"
  "$PYTHON_CMD" -m venv "$VENV_DIR"
  PYTHON_BIN="$VENV_DIR/bin/python"
fi

# [Section: dependency install]
# Install required packages each run so first launch works without extra steps.
echo "Installing/refreshing dependencies"
"$PYTHON_BIN" -m pip install -r "$ROOT_DIR/requirements.txt"

# [Section: running-instance shortcut]
# If the app is already running locally, open it and stop to avoid duplicate server processes.
RUNNING_PORT="$(find_running_port || true)"
if [[ -n "$RUNNING_PORT" ]]; then
  APP_URL="http://127.0.0.1:$RUNNING_PORT"
  echo "App already running at $APP_URL"
  open "$APP_URL" >/dev/null 2>&1 || true
  exit 0
fi

# [Section: start and auto-open]
# Pick the launch port up front, start run.sh in the background with PORT exported,
# then poll until listening before opening the browser.
PORT="$(find_open_port)"
export PORT
APP_URL="http://127.0.0.1:$PORT"

echo "Starting app on $APP_URL"
"$ROOT_DIR/run.sh" &
APP_PID=$!

DEADLINE=$(( $(date +%s) + 20 ))
OPENED=0
while [[ $(date +%s) -lt $DEADLINE ]]; do
  if lsof -i TCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    open "$APP_URL" >/dev/null 2>&1 || true
    OPENED=1
    break
  fi
  if ! kill -0 "$APP_PID" >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done

if [[ $OPENED -eq 0 ]]; then
  echo "App is still starting. Open $APP_URL in your browser once ready."
fi

# [Section: attach lifecycle]
# Keep this launcher attached to the Flask process so Ctrl+C still stops the app.
wait "$APP_PID"
