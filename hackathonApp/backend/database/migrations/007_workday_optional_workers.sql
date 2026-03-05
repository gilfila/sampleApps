-- Migration 007: Make workers.workday_id nullable for local-only users
-- Workday integration is optional; users can be created in-app without Workday.

ALTER TABLE workers ALTER COLUMN workday_id DROP NOT NULL;
