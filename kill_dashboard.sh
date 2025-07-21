#!/bin/bash
# Quick dashboard port cleanup script

echo "🧹 Cleaning up AI Pokemon Dashboard ports..."

# Dashboard ports
PORTS=(3000 5173 8888 8889)

for PORT in "${PORTS[@]}"; do
    echo "🔍 Checking port $PORT..."
    
    # Find process using the port
    PID=$(lsof -ti:$PORT)
    
    if [ ! -z "$PID" ]; then
        echo "⚠️ Port $PORT is used by process $PID"
        
        # Get process info
        PROCESS_INFO=$(ps -p $PID -o comm= 2>/dev/null)
        echo "   Process: $PROCESS_INFO"
        
        # Kill the process
        echo "🔨 Killing process $PID..."
        kill $PID 2>/dev/null
        
        # Wait a moment and check if it's gone
        sleep 2
        if ! kill -0 $PID 2>/dev/null; then
            echo "✅ Process $PID terminated"
        else
            echo "🔨 Force killing process $PID..."
            kill -9 $PID 2>/dev/null
            sleep 1
            if ! kill -0 $PID 2>/dev/null; then
                echo "✅ Process $PID force killed"
            else
                echo "❌ Could not kill process $PID"
            fi
        fi
    else
        echo "✅ Port $PORT is free"
    fi
done

echo "🎯 Port cleanup complete"
echo ""
echo "You can now start the dashboard with:"
echo "python dashboard.py --config config_emulator.json"