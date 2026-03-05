#!/bin/bash
# Start script for Hackathon App backend server

cd "$(dirname "$0")"

# Set default environment variables if not set
export FLASK_ENV=${FLASK_ENV:-development}
export DATABASE_URL=${DATABASE_URL:-sqlite:///hackathon_app.db}
export SECRET_KEY=${SECRET_KEY:-dev-secret-key-for-local-testing}
export PORT=${PORT:-5000}
export SOCKETIO_CORS_ORIGINS=${SOCKETIO_CORS_ORIGINS:-*}

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start the server
echo "Starting Hackathon App server on port $PORT..."
echo "Environment: $FLASK_ENV"
echo "Database: $DATABASE_URL"
echo ""
python3 run.py
