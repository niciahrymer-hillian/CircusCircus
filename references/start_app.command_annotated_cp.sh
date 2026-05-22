#!/usr/bin/env bash
# [Section: resolve root]
# Find the project root from the script location.
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# [Section: delegate launcher]
# Delegate to start_app.sh so all setup logic stays in one place.
exec "$ROOT_DIR/start_app.sh"
