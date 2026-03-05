"""Run database migrations."""
import os
import sys
import json
from pathlib import Path
import psycopg

LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".cursor", "debug-fae6b4.log")

def _debug_log(message, data, hypothesis_id="H1"):
    try:
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps({"sessionId": "fae6b4", "hypothesisId": hypothesis_id, "location": "run_migrations.py", "message": message, "data": data, "timestamp": __import__("time").time() * 1000}) + "\n")
    except Exception:
        pass


def run_migrations(database_url):
    """Run all pending migrations."""
    # Use libpq-style URL (postgresql://); strip SQLAlchemy driver suffix if present
    conninfo = database_url.split("?")[0].replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(conninfo)
    cur = conn.cursor()

    # Create migrations table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(50) PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()

    # Get applied migrations
    cur.execute("SELECT version FROM schema_migrations")
    applied = {row[0] for row in cur.fetchall()}

    # Find migration files
    migrations_dir = Path(__file__).parent / 'migrations'
    migration_files = sorted(migrations_dir.glob('*.sql'))
    migration_files = [f for f in migration_files if 'rollback' not in f.name]

    for migration_file in migration_files:
        version = migration_file.stem  # e.g., "003_ticket_sequence"
        if version in applied:
            print(f"  {version} (already applied)")
            continue

        print(f"  Applying {version}...")
        # #region agent log
        if version == "003_ticket_sequence":
            try:
                cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = 'tickets')")
                tickets_exists = cur.fetchone()[0]
                setval_input = None
                if tickets_exists:
                    cur.execute("SELECT COALESCE(MAX(ticket_number), 0) FROM tickets")
                    setval_input = cur.fetchone()[0]
                _debug_log("003 setval input", {"tickets_exists": tickets_exists, "setval_input": setval_input}, "H1")
            except Exception as e:
                _debug_log("003 pre-check error", {"error": str(e)}, "H1")
        # #endregion
        with open(migration_file) as f:
            cur.execute(f.read())

        cur.execute(
            "INSERT INTO schema_migrations (version) VALUES (%s)",
            (version,)
        )
        conn.commit()
        print(f"  {version} applied successfully")

    cur.close()
    conn.close()
    print("All migrations up to date.")


if __name__ == '__main__':
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    run_migrations(database_url)
