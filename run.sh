# export PORT=5006
export SECRET_KEY="kristofer"
# honcho start

# Choose an open port starting at 5006 to avoid startup failures.
PORT="${PORT:-5006}"
while lsof -i TCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; do
	PORT=$((PORT + 1))
done

echo "Starting Flask on port $PORT"

# you can ALSO or RATHER use the following command to run the app
cd ./forum && flask run --port="$PORT"
