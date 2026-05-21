# export PORT=5006
export SECRET_KEY="kristofer"
# honcho start

# Choose an open port starting at 5006 to avoid startup failures.
PORT="${PORT:-5006}"
while lsof -i TCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; do
	PORT=$((PORT + 1))
done

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Starting Flask on port $PORT"

# you can ALSO or RATHER use the following command to run the app
if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
	PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
	PYTHON_BIN="python3"
fi

cd "$ROOT_DIR/forum" && "$PYTHON_BIN" -m flask run --port="$PORT"
