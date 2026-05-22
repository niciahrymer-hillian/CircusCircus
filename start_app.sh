#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

ensure_postgres_available() {
  local env_file="$ROOT_DIR/.env"
  local db_url=""

  if [[ -f "$env_file" ]]; then
    db_url="$(grep '^DATABASE_URL=' "$env_file" | tail -n 1 | cut -d= -f2- || true)"
  fi

  if [[ "$db_url" != postgresql://* && "$db_url" != postgresql+psycopg2://* ]]; then
    return 0
  fi

  if ! command -v docker >/dev/null 2>&1; then
    echo "PostgreSQL DATABASE_URL detected, but Docker is not installed or not on PATH."
    echo "Proceeding with local PostgreSQL expectation."
    return 0
  fi

  if ! docker info >/dev/null 2>&1; then
    echo "PostgreSQL DATABASE_URL detected, but Docker daemon is not running."
    echo "Proceeding with local PostgreSQL expectation."
    return 0
  fi

  if [[ -f "$ROOT_DIR/docker-compose.yml" ]]; then
    echo "Starting PostgreSQL container service (db)..."
    if ! docker compose -f "$ROOT_DIR/docker-compose.yml" up -d db >/dev/null 2>&1; then
      echo "Could not start docker compose db service; continuing with existing PostgreSQL setup."
    fi
  fi
}

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

echo "Installing/refreshing dependencies"
"$PYTHON_BIN" -m pip install -r "$ROOT_DIR/requirements.txt"

ensure_postgres_available

RUNNING_PORT="$(find_running_port || true)"
if [[ -n "$RUNNING_PORT" ]]; then
  APP_URL="http://127.0.0.1:$RUNNING_PORT"
  echo "App already running at $APP_URL"
  open "$APP_URL" >/dev/null 2>&1 || true
  exit 0
fi

PORT="$(find_open_port)"
export PORT
APP_URL="http://127.0.0.1:$PORT"

echo "Starting app on $APP_URL"
"$ROOT_DIR/run.sh" &
APP_PID=$!

# Open the browser after Flask starts listening.
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

wait "$APP_PID"
