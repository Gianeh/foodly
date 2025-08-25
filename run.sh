#!/bin/bash
# Exit on error
set -e

# Function to kill processes on a given port
kill_on_port() {
    PORT=$1
    echo "Checking for process on port $PORT..."
    # Use lsof to find the PID listening on the specified TCP port
    PID=$(lsof -t -iTCP:$PORT)

    if [ -n "$PID" ]; then
        echo "Process found on port $PORT with PID $PID. Killing it..."
        kill -9 $PID
        sleep 1 # Give it a moment to release the port
    else
        echo "No process found on port $PORT."
    fi
}

# Clean up previous runs
kill_on_port 8000
kill_on_port 8001

# Run App (Web UI)
echo "Starting Web UI on http://127.0.0.1:8000"
uvicorn foodly.app.main:app --host 0.0.0.0 --port 8000 --reload &
APP_PID=$!

# Run Agent
echo "Starting Agent on http://127.0.0.1:8001"
uvicorn foodly.agent.main:app --host 0.0.0.0 --port 8001 --reload &
AGENT_PID=$!

# Wait for any process to exit
wait -n $APP_PID $AGENT_PID

# Clean up on exit
kill $APP_PID $AGENT_PID
