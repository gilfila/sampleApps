"""Sync orchestrator for on-demand Workday sync operations.

Coordinates single-user and bulk sync workflows, manages circuit breaker
state, creates audit records, and handles graceful degradation.
"""

import uuid
import logging
import threading
from datetime import datetime
from app import db
from app.models import (
    Worker, SyncJob, SyncJobItem, SyncJobStatus,
    SyncTriggerType,
)
from app.services.workday_sync import WorkdaySync
from app.services.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

# Module-level circuit breaker (shared across requests)
workday_circuit = CircuitBreaker(failure_threshold=5, cooldown_seconds=300)

# Lock to prevent concurrent bulk syncs
_bulk_sync_lock = threading.Lock()
_active_bulk_job_id = None


class SyncOrchestrator:
    """Orchestrates on-demand Workday sync operations."""

    def __init__(self):
        self.workday = WorkdaySync()

    def sync_single_user(self, workday_id, initiated_by_id=None,
                         trigger_type=SyncTriggerType.MANUAL):
        """Sync a single user from Workday.

        Returns:
            Tuple of (SyncJob, Worker). If the circuit breaker is open,
            returns (None, cached_worker) as a fallback.
        """
        if workday_circuit.is_open:
            return self._fallback_cached(workday_id, "Circuit breaker open")

        # Create sync job
        job = SyncJob(
            id=str(uuid.uuid4()),
            trigger_type=trigger_type,
            initiated_by_id=initiated_by_id,
            status=SyncJobStatus.RUNNING,
            started_at=datetime.utcnow(),
            total_count=1
        )
        db.session.add(job)
        db.session.flush()

        try:
            # Fetch from Workday
            worker_data = self.workday.fetch_single_worker(workday_id)
            custom_data = self.workday.fetch_worker_custom_object(workday_id)

            workday_circuit.record_success()

            # Find or create local worker
            worker = Worker.query.filter_by(workday_id=workday_id).first()
            if not worker:
                worker = Worker(workday_id=workday_id)
                db.session.add(worker)
                db.session.flush()

            # Track changes
            changes = {}
            field_map = {
                'name': worker_data.get('Name'),
                'email': worker_data.get('Email'),
                'employee_id': worker_data.get('Employee_ID'),
                'department': worker_data.get('Department'),
                'job_title': worker_data.get('Job_Title'),
                'manager': worker_data.get('Manager'),
            }
            if custom_data:
                field_map.update({
                    'table': custom_data.get('Table'),
                    'team_name': custom_data.get('Team_Name'),
                    'tenant_url': custom_data.get('Tenant_URL'),
                    'company': custom_data.get('Company'),
                })

            for field, new_value in field_map.items():
                if new_value is None:
                    continue
                old_value = getattr(worker, field)
                if old_value != new_value:
                    changes[field] = {'old': old_value, 'new': new_value}
                    setattr(worker, field, new_value)

            # Update sync metadata
            worker.last_synced_at = datetime.utcnow()
            worker.sync_status = 'synced'
            worker.sync_error = None

            # Create job item
            item = SyncJobItem(
                job_id=job.id,
                worker_id=worker.id,
                workday_id=workday_id,
                status='synced',
                changed_fields=changes
            )
            db.session.add(item)

            # Complete job
            job.status = SyncJobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.success_count = 1

            db.session.commit()
            return job, worker

        except Exception as e:
            workday_circuit.record_failure()
            logger.error(f"Sync failed for {workday_id}: {e}")

            job.status = SyncJobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error_count = 1
            job.error_summary = str(e)

            item = SyncJobItem(
                job_id=job.id,
                workday_id=workday_id,
                status='error',
                error_message=str(e)
            )
            db.session.add(item)
            db.session.commit()

            raise

    def sync_bulk(self, initiated_by_id, filter_criteria=None, force=False):
        """Start a bulk sync. Returns job immediately; processing is async.

        Returns:
            Tuple of (SyncJob, active_job_id). If a bulk sync is already
            running, returns (None, active_job_id).
        """
        global _active_bulk_job_id

        if not _bulk_sync_lock.acquire(blocking=False):
            return None, _active_bulk_job_id

        try:
            # Determine workers to sync
            query = Worker.query
            if filter_criteria:
                if filter_criteria.get('team_name'):
                    query = query.filter_by(team_name=filter_criteria['team_name'])
                if filter_criteria.get('table'):
                    query = query.filter_by(table=filter_criteria['table'])

            workers = [w for w in query.all() if w.workday_id]

            job = SyncJob(
                id=str(uuid.uuid4()),
                trigger_type=SyncTriggerType.BULK,
                initiated_by_id=initiated_by_id,
                status=SyncJobStatus.RUNNING,
                started_at=datetime.utcnow(),
                total_count=len(workers),
                filter_criteria=filter_criteria
            )
            db.session.add(job)
            db.session.commit()

            _active_bulk_job_id = job.id

            # Capture app for background thread context
            from flask import current_app
            app = current_app._get_current_object()

            thread = threading.Thread(
                target=self._run_bulk_sync,
                args=(app, job.id, [w.workday_id for w in workers], force),
                daemon=True
            )
            thread.start()

            return job, None
        except Exception:
            _bulk_sync_lock.release()
            raise

    def _run_bulk_sync(self, app, job_id, workday_ids, force):
        """Background worker for bulk sync. Processes in batches."""
        global _active_bulk_job_id

        with app.app_context():
            try:
                batch_size = 50
                for i in range(0, len(workday_ids), batch_size):
                    batch = workday_ids[i:i + batch_size]
                    for wid in batch:
                        try:
                            self.sync_single_user(
                                wid,
                                trigger_type=SyncTriggerType.BULK
                            )
                        except Exception as e:
                            logger.error(f"Bulk sync error for {wid}: {e}")
                            continue

                # Mark bulk job as completed
                job = db.session.get(SyncJob, job_id)
                if job:
                    items = SyncJobItem.query.filter_by(job_id=job_id).all()
                    success = sum(1 for it in items if it.status == 'synced')
                    errors = sum(1 for it in items if it.status == 'error')
                    job.success_count = success
                    job.error_count = errors
                    job.status = SyncJobStatus.COMPLETED if errors == 0 else SyncJobStatus.PARTIAL
                    job.completed_at = datetime.utcnow()
                    db.session.commit()
            finally:
                _active_bulk_job_id = None
                _bulk_sync_lock.release()

    def _fallback_cached(self, workday_id, reason):
        """Return cached data when Workday is unavailable."""
        worker = Worker.query.filter_by(workday_id=workday_id).first()
        if worker:
            worker.sync_status = 'stale'
            db.session.commit()
        return None, worker
