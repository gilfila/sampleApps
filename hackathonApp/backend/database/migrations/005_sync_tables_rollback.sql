DROP TABLE IF EXISTS sync_job_items CASCADE;
DROP TABLE IF EXISTS sync_jobs CASCADE;
ALTER TABLE workers
    DROP COLUMN IF EXISTS last_synced_at,
    DROP COLUMN IF EXISTS sync_status,
    DROP COLUMN IF EXISTS sync_error;
