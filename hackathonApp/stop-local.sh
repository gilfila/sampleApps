#!/bin/bash

# Hackathon App - Stop Local Servers
echo "🛑 Stopping Hackathon App..."

# Kill backend
if [ -f .backend.pid ]; then
    BACKEND_PID=$(cat .backend.pid)
    kill $BACKEND_PID 2>/dev/null && echo "✓ Backend stopped (PID: $BACKEND_PID)" || echo "  Backend already stopped"
    rm .backend.pid
fi

# Kill frontend
if [ -f .frontend.pid ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    kill $FRONTEND_PID 2>/dev/null && echo "✓ Frontend stopped (PID: $FRONTEND_PID)" || echo "  Frontend already stopped"
    rm .frontend.pid
fi

# Clean up any remaining processes
pkill -f "python.*run.py" 2>/dev/null && echo "✓ Cleaned up backend processes"
pkill -f "react-scripts start" 2>/dev/null && echo "✓ Cleaned up frontend processes"

echo ""
echo "✅ All servers stopped"
