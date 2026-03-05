# Deployment Guide

## Prerequisites

- PostgreSQL 12+ database
- Python 3.11+ runtime
- Node.js 18+ (for frontend build)
- SSL certificate for HTTPS

## Deployment Steps

### 1. Database Setup

```bash
# Create database
createdb hackathon_prod

# Set DATABASE_URL environment variable
export DATABASE_URL=postgresql://user:password@host/hackathon_prod

# Run migrations
python backend/database/run_migrations.py
```

### 2. Backend Deployment (Flask)

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Set all required environment variables (see environment-setup.md)
export SECRET_KEY=...
export CORS_ORIGINS=https://yourdomain.com
# ... (all other env vars)

# Run with Gunicorn (production WSGI server)
gunicorn -w 4 -b 0.0.0.0:5000 --worker-class eventlet run:app
```

### 3. Frontend Deployment (React)

```bash
# Build production bundle
cd frontend
npm install
npm run build

# Serve with nginx or any static file server
# Copy build/ contents to your web server
```

### 4. WebSocket Configuration

- Use eventlet or gevent worker class with Gunicorn
- For >500 concurrent connections, consider using Redis message queue:
  ```python
  socketio.init_app(app, message_queue='redis://localhost:6379')
  ```

### 5. Security Checklist

- [ ] All environment variables set (no defaults)
- [ ] HTTPS enabled with valid certificate
- [ ] CORS origins locked to specific domains
- [ ] SECRET_KEY is random and secure
- [ ] MFA_ENCRYPTION_KEY is random and secure
- [ ] Database has strong password
- [ ] Rate limiting configured (use Redis in production)
- [ ] Security headers enabled
- [ ] Debug mode disabled (`FLASK_ENV=production`)

### 6. Health Checks

- Backend health: `GET /api/health`
- Database connectivity: Check migrations table
- WebSocket connectivity: Use wscat or socket.io-client

### 7. Monitoring

- Log aggregation (use logging_config.py output)
- Error tracking (Sentry or similar)
- Performance monitoring (New Relic, DataDog, etc.)
- Rate limit metrics (track 429 responses)

### 8. Backup Strategy

- Database: Daily PostgreSQL backups
- Environment variables: Securely store in vault (HashiCorp Vault, AWS Secrets Manager, etc.)
- Application code: Git repository

## Rollback Plan

If deployment fails:

1. Revert to previous Git commit
2. Rollback database migrations (use `*_rollback.sql` scripts)
3. Restore previous environment variables
4. Restart services

## Load Testing

Before the hackathon:

- Run load test with 1000 concurrent users (see `backend/tests/load/`)
- Monitor response times (<500ms target)
- Check WebSocket connection stability
- Verify rate limiting does not block legitimate users
