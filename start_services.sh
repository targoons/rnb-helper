
# Kill existing processes (Zombie Prevention)
pkill -9 -f "node server.js" 2>/dev/null
pkill -9 -f "python3 app/main.py" 2>/dev/null


# Kill existing processes (Zombie Prevention)
echo "Stopping existing services..."
pkill -9 -f "node server.js" 2>/dev/null
pkill -9 -f "python3 app/main.py" 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null
sleep 1

# Start Node.js Calc Service
echo "Starting Calc Service..."
cd calc_service
npm install
node server.js &
NODE_PID=$!
cd ..

# Wait for Node to initialize
sleep 2

# Start Python App
echo "Starting Python App..."
export PYTHONPATH=$PYTHONPATH:.
python3 -m app.main

# Cleanup on exit
trap "kill $NODE_PID 2>/dev/null" EXIT
