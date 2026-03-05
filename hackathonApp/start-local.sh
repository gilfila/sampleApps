#!/bin/bash

# Hackathon App - Local Startup Script
# On Render: FLASK_ENV=production and startCommand "cd backend && python run.py" use
# config.ProductionConfig, which normalizes postgres:// to postgresql:// for SQLAlchemy.
set -e

APP_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_ROOT"

# Force development config for local runs (Render sets FLASK_ENV=production)
export FLASK_ENV=development

# Create log files up front so they always exist and are in project root
touch "$APP_ROOT/backend.log" "$APP_ROOT/frontend.log"

echo "🚀 Starting Hackathon App Locally..."
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if PostgreSQL is running (TCP connect with timeout; avoids pg_isready hang on some systems)
echo "📊 Checking PostgreSQL..."
if ! python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(3)
try:
    s.connect(('127.0.0.1', 5432))
    s.close()
except Exception:
    exit(1)
" 2>/dev/null; then
    echo -e "${RED}❌ PostgreSQL is not running on 127.0.0.1:5432${NC}"
    echo ""
    echo "Please start PostgreSQL first:"
    echo "  - macOS: brew services start postgresql@14"
    echo "  - Linux: sudo systemctl start postgresql"
    echo "  - Docker: docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres --name hackathon-db postgres:14"
    echo ""
    exit 1
fi
echo -e "${GREEN}✓ PostgreSQL is running${NC}"

# Create database if it doesn't exist
# Homebrew PostgreSQL uses your macOS user as the default superuser (no "postgres" role).
# Docker postgres image uses POSTGRES_USER=postgres. Set POSTGRES_USER in env to override.
# Use 127.0.0.1 to avoid IPv6/GSSAPI issues on macOS.
# Connect to "postgres" system DB first (psql defaults to a DB named after the user otherwise).
PSQL_USER="${POSTGRES_USER:-$(whoami)}"
PSQL_HOST="${POSTGRES_HOST:-127.0.0.1}"
PSQL_SYSTEM_DB="${POSTGRES_SYSTEM_DB:-postgres}"
echo ""
echo "🗄️  Setting up database (user: $PSQL_USER)..."
psql -h "$PSQL_HOST" -U "$PSQL_USER" -d "$PSQL_SYSTEM_DB" -tc "SELECT 1 FROM pg_database WHERE datname = 'hackathon_dev'" 2>/dev/null | grep -q 1 || \
    psql -h "$PSQL_HOST" -U "$PSQL_USER" -d "$PSQL_SYSTEM_DB" -c "CREATE DATABASE hackathon_dev"
echo -e "${GREEN}✓ Database 'hackathon_dev' ready${NC}"
if [ "$PSQL_USER" != "postgres" ]; then
    echo -e "${YELLOW}  Tip: In backend/.env set DATABASE_URL=postgresql://$PSQL_USER@$PSQL_HOST:5432/hackathon_dev${NC}"
fi

# Check if .env exists and has required keys
echo ""
echo "🔐 Checking environment configuration..."
if [ ! -f backend/.env ]; then
    echo -e "${RED}❌ backend/.env not found${NC}"
    echo "Creating template .env file..."
    cp backend/.env backend/.env.backup 2>/dev/null || true
fi

# Generate SECRET_KEY if not set
if grep -q "your-secret-key-here" backend/.env 2>/dev/null; then
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i.bak "s/your-secret-key-here-change-this-in-production/$SECRET_KEY/" backend/.env
    echo -e "${GREEN}✓ Generated SECRET_KEY${NC}"
fi

# Generate MFA_ENCRYPTION_KEY if not set (std lib only - runs before venv has cryptography)
if grep -q "your-fernet-key-here" backend/.env 2>/dev/null; then
    MFA_KEY=$(python3 -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())")
    sed -i.bak "s/your-fernet-key-here/$MFA_KEY/" backend/.env
    echo -e "${GREEN}✓ Generated MFA_ENCRYPTION_KEY${NC}"
fi

echo -e "${GREEN}✓ Environment configured${NC}"

# Install backend dependencies if needed
echo ""
echo "📦 Checking backend dependencies..."
cd backend
if [ ! -d "venv" ] && [ ! -d "../.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Backend dependencies installed${NC}"
else
    if [ -d "venv" ]; then
        source venv/bin/activate
    elif [ -d "../.venv" ]; then
        source ../.venv/bin/activate
    fi
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
    pip install -r requirements.txt -q
    echo -e "${GREEN}✓ Backend dependencies synced${NC}"
fi

# Create base tables from Flask models (workers, tickets, chat_messages, etc.)
# so migrations 003+ can run (they reference these tables or extend them).
# FLASK_ENV=development (set above) ensures DevelopmentConfig is used and config loads without error.
echo ""
echo "📋 Creating base tables..."
export $(cat .env | grep -v '^#' | xargs)
export FLASK_ENV=development
python -c "from app import create_app; create_app()"
echo -e "${GREEN}✓ Base tables ready${NC}"

# Run migrations
echo ""
echo "🔄 Running database migrations..."
python database/run_migrations.py
echo -e "${GREEN}✓ Migrations complete${NC}"

# Seed local dev users (admin, hacker, expert @hackathon.com / password: password)
echo ""
echo "👤 Seeding local users..."
python seed_users.py 2>/dev/null || true
echo -e "${GREEN}✓ Seed users ready${NC}"

# Start backend server in background (FLASK_ENV=development from above)
echo ""
echo "🌐 Starting backend server..."
export FLASK_ENV=development
python run.py > "$APP_ROOT/backend.log" 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend running on http://localhost:5000 (PID: $BACKEND_PID)${NC}"
cd ..

# Install frontend dependencies if needed
echo ""
echo "📦 Checking frontend dependencies..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
    echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
else
    echo -e "${GREEN}✓ Frontend dependencies ready${NC}"
fi

# Start frontend dev server
echo ""
echo "🎨 Starting frontend dev server..."
npm start > "$APP_ROOT/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}✓ Frontend running on http://localhost:3000 (PID: $FRONTEND_PID)${NC}"
cd ..

# Wait for servers to start
echo ""
echo "⏳ Waiting for servers to be ready..."
sleep 5

# Check if servers are running
BACKEND_RUNNING=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000 || echo "000")
FRONTEND_RUNNING=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 || echo "000")

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Hackathon App Started Successfully!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📱 Frontend:  http://localhost:3000"
echo "🔧 Backend:   http://localhost:5000"
echo ""
echo "🔑 Log in with:  admin@hackathon.com  /  password"
echo "   (or hacker@hackathon.com / expert@hackathon.com, same password)"
echo "📄 Logs (run from project root):"
echo "   tail -f \"$APP_ROOT/backend.log\" \"$APP_ROOT/frontend.log\""
echo "   # or in separate terminals: tail -f backend.log  and  tail -f frontend.log"
echo ""
echo "Process IDs:"
echo "  Backend:  $BACKEND_PID"
echo "  Frontend: $FRONTEND_PID"
echo ""
echo "To stop the servers:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo "  # or run: ./stop-local.sh"
echo ""
echo -e "${YELLOW}Note: First-time setup may take a moment for frontend to compile${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Save PIDs for stop script
echo "$BACKEND_PID" > "$APP_ROOT/.backend.pid"
echo "$FRONTEND_PID" > "$APP_ROOT/.frontend.pid"

# Keep script running and show logs (use absolute paths so it works from any cwd)
echo "Press Ctrl+C to stop both servers..."
tail -f "$APP_ROOT/backend.log" "$APP_ROOT/frontend.log" 2>/dev/null || true
