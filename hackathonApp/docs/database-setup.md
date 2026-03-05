# Database Setup Guide

## Initial Setup

### 1. Install PostgreSQL 12+

```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql
```

### 2. Create Database

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE hackathon_dev;
CREATE USER hackathon_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE hackathon_dev TO hackathon_user;
\q
```

### 3. Set DATABASE_URL

```bash
export DATABASE_URL=postgresql://hackathon_user:secure_password@localhost/hackathon_dev
```

### 4. Run Migrations

```bash
python backend/database/run_migrations.py
```

## Migration Management

### Apply Migrations

```bash
python backend/database/run_migrations.py
```

### Rollback Migration

```bash
# Rollback a specific migration by running its rollback script
psql $DATABASE_URL < backend/database/migrations/006_mfa_tables_rollback.sql
```

### Check Applied Migrations

```sql
SELECT * FROM schema_migrations ORDER BY applied_at;
```

### Migration Files

| File | Description |
|------|-------------|
| `003_ticket_sequence.sql` | PostgreSQL sequence for atomic ticket numbering |
| `004_chat_tables.sql` | Channels, memberships, read receipts, mentions |
| `005_sync_tables.sql` | Workday sync tracking (jobs, items, worker columns) |
| `006_mfa_tables.sql` | MFA configuration, trusted devices, audit log |

Each migration has a corresponding `*_rollback.sql` file for reversal.

## Database Maintenance

### Backup

```bash
pg_dump -U hackathon_user hackathon_prod > backup_$(date +%Y%m%d).sql
```

### Restore

```bash
psql -U hackathon_user hackathon_prod < backup_20260213.sql
```

### Performance Tuning

- Ensure indexes exist on foreign keys
- Run `ANALYZE` periodically
- Monitor slow queries with `pg_stat_statements`
