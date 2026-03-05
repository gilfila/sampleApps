# Local Development Setup Guide

## Quick Start (Automated)

```bash
# 1. Make sure PostgreSQL is running (see options below)
# 2. Run the startup script
./start-local.sh
```

This will automatically:
- ✅ Check PostgreSQL connection
- ✅ Create database `hackathon_dev`
- ✅ Generate security keys
- ✅ Install dependencies
- ✅ Run migrations
- ✅ Seed local users (admin, hacker, expert)
- ✅ Start backend (port 5000)
- ✅ Start frontend (port 3000)

**Log in at http://localhost:3000** with:
- **Email:** `admin@hackathon.com` (or `hacker@hackathon.com`, `expert@hackathon.com`)
- **Password:** `password`

## Prerequisites

### Option 1: PostgreSQL via Homebrew (macOS)
```bash
brew install postgresql@14
brew services start postgresql@14

# Create postgres user if needed
createuser -s postgres
```

### Option 2: PostgreSQL via Docker
```bash
docker run -d \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=postgres \
  --name hackathon-db \
  postgres:14

# To stop: docker stop hackathon-db
# To start: docker start hackathon-db
```

### Option 3: PostgreSQL via apt (Linux)
```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

## Manual Setup (Step-by-Step)

If you prefer manual control:

### 1. Set Up Database
```bash
# Create database
psql -U postgres -c "CREATE DATABASE hackathon_dev"

# Verify connection
psql -U postgres -d hackathon_dev -c "SELECT version()"
```

### 2. Configure Environment
```bash
cd backend

# The .env file is already created with:
# - Generated SECRET_KEY
# - Generated MFA_ENCRYPTION_KEY
# - Development settings

# Update these if needed:
nano .env  # Edit DATABASE_URL, Workday credentials, etc.
```

### 3. Install Backend Dependencies
```bash
cd backend

# Use existing virtual environment or create new one
source ../.venv/bin/activate  # or: python -m venv venv && source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 4. Run Database Migrations
```bash
cd backend
export $(cat .env | grep -v '^#' | xargs)
python database/run_migrations.py
```

Expected output:
```
  003_ticket_sequence applied successfully
  004_chat_tables applied successfully
  005_sync_tables applied successfully
  006_mfa_tables applied successfully
All migrations up to date.
```

### 5. Start Backend Server
```bash
cd backend
python run.py

# Server should start on http://localhost:5000
```

### 6. Install Frontend Dependencies (in new terminal)
```bash
cd frontend
npm install
```

### 7. Start Frontend Dev Server
```bash
cd frontend
npm start

# Frontend should open automatically at http://localhost:3000
```

## Stopping the Application

```bash
# Use the stop script
./stop-local.sh

# Or manually
kill $(cat .backend.pid)
kill $(cat .frontend.pid)

# Or find and kill processes
pkill -f "python.*run.py"
pkill -f "react-scripts start"
```

## Troubleshooting

### PostgreSQL Connection Errors
```bash
# Check if PostgreSQL is running
pg_isready -h localhost -p 5432

# Check PostgreSQL logs
tail -f /usr/local/var/log/postgresql@14.log  # Homebrew
docker logs hackathon-db  # Docker
```

### Port Already in Use
```bash
# Find what's using port 5000
lsof -i :5000
# Kill it
kill -9 <PID>

# Find what's using port 3000
lsof -i :3000
# Kill it
kill -9 <PID>
```

If port 3000 is busy and you want to keep the other process running, start the frontend on another port:
```bash
cd frontend && PORT=3001 npm start
# Then open http://localhost:3001
```

### Proxy error: Could not proxy request to http://localhost:5000 (ECONNREFUSED)

The frontend proxies `/api/*` to the backend on port 5000. This error means **the backend is not running** when the frontend tries to call it.

**Fix:**
1. Start the backend first: `cd backend && source venv/bin/activate && python run.py` (or use `./start-local.sh`, which starts both backend and frontend).
2. Ensure nothing is blocking port 5000 and the backend process is actually listening (you should see "Running on http://0.0.0.0:5000" in the backend terminal or `backend.log`).

### Warning: Ignoring extra certs from `/path/to/your-corporate-ca.pem`

Node is trying to load a custom CA certificate (often from `NODE_EXTRA_CA_CERTS`) but the file doesn’t exist. You can ignore the warning, or clear it for local dev:

```bash
unset NODE_EXTRA_CA_CERTS
# Then start the frontend again
cd frontend && npm start
```

To make it permanent for this project, add to `frontend/.env`: `NODE_EXTRA_CA_CERTS=` (empty), or ensure the variable points to a real `.pem` file if you need corporate TLS.

### Database Migration Errors
```bash
# Reset migrations (⚠️ destroys data)
psql -U postgres -c "DROP DATABASE hackathon_dev"
psql -U postgres -c "CREATE DATABASE hackathon_dev"
cd backend && python database/run_migrations.py
```

### Frontend Build Errors
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Backend Import Errors
```bash
cd backend
pip install -r requirements.txt --force-reinstall
```

### "Email not found. Please contact admin." when registering

Registration only allows emails that already exist in the `workers` table. Without Workday sync, add invitees via CSV:

1. Create a CSV with columns `email`, `name`, `role` (role optional, default: hacker). See `backend/invites_example.csv`.
2. From the backend directory: `python seed_invites_from_csv.py path/to/your_invites.csv`
3. Those users can then go to `/register`, enter their email, and set a password.

Alternatively, log in as an admin and create workers via the API (`POST /api/workers`), or use the three seeded local users: `admin@hackathon.com`, `hacker@hackathon.com`, `expert@hackathon.com` (password: `password`).

## Creating Your First Admin User

Once the app is running:

```bash
cd backend
python create_admin.py
```

Follow prompts to create an admin account.

## Running Tests

### Backend Tests
```bash
cd backend
pytest tests/ -v --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Load Testing (WebSocket stress test)
```bash
cd backend
python tests/load/websocket_stress_test.py
```

## Workday Integration (Optional for Local Dev)

The app can run without Workday integration for local development. To enable:

1. Get Workday credentials (OAuth 2.0)
2. Update `backend/.env`:
```bash
WORKDAY_TENANT=your-tenant
WORKDAY_CLIENT_ID=your-client-id
WORKDAY_CLIENT_SECRET=your-client-secret
WORKDAY_REFRESH_TOKEN=your-refresh-token
```

3. Test sync:
```bash
# Must be admin user
curl -X POST http://localhost:5000/api/admin/sync/bulk \
  -H "Content-Type: application/json" \
  -b "session=<your-session-cookie>"
```

## Development Workflow

1. **Make code changes** in `backend/` or `frontend/src/`
2. **Backend**: Server auto-reloads (Flask debug mode)
3. **Frontend**: Hot module replacement (React dev server)
4. **Run tests** before committing
5. **Check logs**: `tail -f backend.log frontend.log`

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | ✅ | (auto-generated) | Flask session key |
| `DATABASE_URL` | ✅ | postgresql://... | PostgreSQL connection |
| `CORS_ORIGINS` | ✅ | http://localhost:3000 | Allowed origins |
| `MFA_ENCRYPTION_KEY` | ✅ | (auto-generated) | Fernet key for MFA |
| `WORKDAY_TENANT` | ❌ | - | Workday tenant name |
| `WORKDAY_CLIENT_ID` | ❌ | - | OAuth client ID |
| `WORKDAY_CLIENT_SECRET` | ❌ | - | OAuth secret |
| `FLASK_ENV` | ❌ | development | Environment mode |
| `FLASK_DEBUG` | ❌ | 1 | Enable debug mode |

## Troubleshooting

### 500 error when logging in

If the backend returns **500** on `POST /api/auth/login`, the most common cause is that **PostgreSQL is not running** but your app is configured to use it.

- Your `backend/.env` likely has `DATABASE_URL=postgresql://...`. When Postgres is down, every request that touches the database (including login) fails and the server returns 500.

**Fix:** Start PostgreSQL, then try again.

- **macOS (Homebrew):** `brew services start postgresql@14`
- **Docker:** `docker start hackathon-db` or run the `docker run ...` command from the Prerequisites section above
- **Linux:** `sudo systemctl start postgresql`

Then restart the app (`./stop-local.sh` then `./start-local.sh` if you use the startup script).

### start-local.sh says "PostgreSQL is not running"

Start Postgres using one of the options in **Prerequisites** above. The script will not start the backend or frontend until Postgres is available on `localhost:5432`.

## Next Steps

- 📖 Read [API Documentation](backend/docs/api/openapi.yaml)
- 🎨 Check [UX Analysis](TEAMANALYSIS.md)
- 🐛 Review [Bug Report](docs/BUG-REPORT.md)
- 🏗️ See [Architecture Docs](docs/design/)

## Support

- 🐛 Report issues: https://github.com/anthropics/claude-code/issues
- 📚 Documentation: See `/docs` folder
- 💬 Questions: Check the README.md
