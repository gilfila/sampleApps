# Environment Setup Guide

## Required Environment Variables

### Core Application

- `SECRET_KEY` - Flask secret key (generate with: `python -c "import secrets; print(secrets.token_hex(32))"`)
- `DATABASE_URL` - PostgreSQL connection string (e.g., `postgresql://user:pass@localhost/hackathon_db`)
- `FLASK_ENV` - Environment mode (`production` or `development`)

### CORS Configuration

- `CORS_ORIGINS` - Comma-separated list of allowed origins (e.g., `https://hackathon.example.com`)

### MFA Configuration

- `MFA_ENCRYPTION_KEY` - AES-256 key for TOTP secrets (generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- `MFA_JWT_SECRET` - JWT secret for mfa_token (can be same as SECRET_KEY)

### Workday Integration

- `WORKDAY_TENANT` - Workday tenant name
- `WORKDAY_CLIENT_ID` - OAuth client ID
- `WORKDAY_CLIENT_SECRET` - OAuth client secret
- `WORKDAY_REFRESH_TOKEN` - OAuth refresh token
- `WORKDAY_CUSTOM_OBJECT_NAME` - Custom object name for hacker data

### Sync Configuration

- `SYNC_CACHE_TTL_IDENTITY` - Cache TTL for identity fields (default: 14400 seconds / 4 hours)
- `SYNC_CACHE_TTL_HACKATHON` - Cache TTL for hackathon fields (default: 3600 seconds / 1 hour)

### Rate Limiting (Optional - defaults to in-memory)

- `RATE_LIMIT_STORAGE_URI` - Redis URI for rate limiting (e.g., `redis://localhost:6379/0`)

## Development Setup

1. Clone repository
2. Create virtual environment: `python -m venv venv`
3. Activate: `source venv/bin/activate` (Unix) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r backend/requirements.txt`
5. Copy `.env.example` to `.env` and fill in values
6. Run migrations: `python backend/database/run_migrations.py`
7. Start backend: `python backend/run.py`
8. Start frontend: `cd frontend && npm install && npm start`

## Production Setup

See [deployment.md](./deployment.md) for the production deployment guide.
