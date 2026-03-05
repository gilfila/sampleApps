-- Migration 005: Workday sync tracking tables
-- Adds sync metadata columns to workers and creates sync_jobs / sync_job_items
-- for the ad-hoc Workday sync integration. Idempotent for safe re-runs.

-- Worker sync columns (add only if missing)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'workers' AND column_name = 'last_synced_at') THEN
    ALTER TABLE workers ADD COLUMN last_synced_at TIMESTAMP;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'workers' AND column_name = 'sync_status') THEN
    ALTER TABLE workers ADD COLUMN sync_status VARCHAR(20) DEFAULT 'never_synced';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'workers' AND column_name = 'sync_error') THEN
    ALTER TABLE workers ADD COLUMN sync_error TEXT;
  END IF;
END $$;

-- Sync jobs
CREATE TABLE IF NOT EXISTS sync_jobs (
    id VARCHAR(36) PRIMARY KEY,
    trigger_type VARCHAR(20) NOT NULL,
    initiated_by_id INTEGER REFERENCES workers(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    total_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    skip_count INTEGER DEFAULT 0,
    filter_criteria JSON,
    error_summary TEXT
);

CREATE INDEX IF NOT EXISTS idx_sync_job_status_started ON sync_jobs(status, started_at);
CREATE INDEX IF NOT EXISTS idx_sync_job_trigger ON sync_jobs(trigger_type, started_at);

-- Sync job items
CREATE TABLE IF NOT EXISTS sync_job_items (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(36) NOT NULL REFERENCES sync_jobs(id),
    worker_id INTEGER REFERENCES workers(id),
    workday_id VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,
    changed_fields JSON,
    error_message TEXT,
    synced_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sync_item_job_status ON sync_job_items(job_id, status);
