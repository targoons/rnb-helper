#!/bin/bash

PID_FILE=".pids"

# Cleanup function
cleanup() {
    echo ""
    echo "Stopping services..."
    
    # Kill PIDs from file
    if [ -f "$PID_FILE" ]; then
        while read -r pid; do
            kill -9 "$pid" 2>/dev/null
        done < "$PID_FILE"
        rm "$PID_FILE"
    fi
    
    # Fallback: Pattern matching (just in case)
    pkill -9 -f "node server.js" 2>/dev/null
    pkill -9 -f "pkh_app.main" 2>/dev/null
    lsof -ti:3000 | xargs kill -9 2>/dev/null
    
    # Kill any children of this shell
    pkill -P $$ 2>/dev/null
}

# Trap signals for cleanup
trap cleanup SIGINT SIGTERM EXIT

# Initial Cleanup
cleanup

# 1. Start Node Service
echo "Starting Calc Service..."
cd calc_service
npm install >/dev/null 2>&1
node server.js >/dev/null &
NODE_PID=$!
cd ..
echo "$NODE_PID" >> "$PID_FILE"

# Wait for Node
sleep 2

# 2. Start Python App
echo "Starting Python App..."
export PYTHONPATH=$PYTHONPATH:.
python3 -m pkh_app.main &
PY_PID=$!
echo "$PY_PID" >> "$PID_FILE"

# Wait for Python (Blocking)
# This keeps the script alive to receive signals.
wait $PY_PID
