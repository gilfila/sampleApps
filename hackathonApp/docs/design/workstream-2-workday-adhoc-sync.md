# Workstream 2: Workday Integration -- Ad-Hoc Sync

## Executive Summary

Replace the current scheduled (interval-based) Workday sync with an on-demand, event-driven sync model. Workday becomes the single authoritative source; PostgreSQL serves as a local read cache. Sync is triggered explicitly by admin actions, first-login events, or bulk-refresh operations. This eliminates the dual-source-of-truth drift that the scheduled model introduces.

---

## 1. Integration Architecture

### 1.1 Data Flow Diagram

```
+------------------------------------------------------------------+
|                        ADMIN / SYSTEM EVENTS                      |
|  [Admin Panel]   [First Login]   [Bulk Refresh]   [Webhook*]     |
+-------+---------------+--------------+---------------+-----------+
        |               |              |               |
        v               v              v               v
+------------------------------------------------------------------+
|                     SYNC ORCHESTRATOR                              |
|  - Validates request                                              |
|  - Checks rate limits (token bucket)                              |
|  - Creates SyncJob record (audit)                                 |
|  - Dispatches to worker thread / queue                            |
+------------------------------------------------------------------+
        |                                       |
        | single user                           | bulk (batched)
        v                                       v
+----------------------------+    +----------------------------+
| WorkdaySyncService         |    | BulkSyncWorker             |
| - get_access_token()       |    | - partition into batches   |
| - fetch_worker(id)         |    |   of 50                    |
| - fetch_custom_object(id)  |    | - rate-limited dispatch    |
| - map & validate fields    |    | - progress tracking        |
+----------------------------+    +----------------------------+
        |                                       |
        v                                       v
+------------------------------------------------------------------+
|                      WORKDAY REST API                              |
|  OAuth2 (refresh_token grant) --> Bearer token                    |
|  GET /workers/:id            GET /customObjects/:name             |
+------------------------------------------------------------------+
        |
        | JSON response
        v
+------------------------------------------------------------------+
|                      CACHE LAYER (PostgreSQL)                      |
|  workers table                                                    |
|  + last_synced_at (per-row)                                       |
|  + sync_status (PENDING | SYNCED | STALE | ERROR)                 |
|  + sync_error (text, nullable)                                    |
|  sync_jobs table (audit log)                                      |
|  sync_job_items table (per-user results within a job)             |
+------------------------------------------------------------------+
        |
        v
+------------------------------------------------------------------+
|                      FLASK API / UI                                |
|  - Reads from PostgreSQL cache                                    |
|  - Displays last_synced_at + stale indicator                      |
|  - Admin: trigger sync, view history, check job status            |
+------------------------------------------------------------------+

* Webhook trigger is a future extension (Workday EIB or Orchestrations).
```

### 1.2 Key Principles

| Principle | Description |
|-----------|-------------|
| **Single source of truth** | Workday owns hacker identity data. PostgreSQL is a read cache only. |
| **Explicit sync** | No background polling. Every sync is traceable to a trigger. |
| **Graceful degradation** | If Workday is unreachable, serve cached data with a staleness indicator. |
| **Audit everything** | Every sync operation is logged with initiator, timestamp, result, and changed fields. |
| **Rate-limit aware** | Bulk operations use batching + exponential backoff to respect Workday API limits. |

### 1.3 Sync Trigger Points

| Trigger | When | Scope | Mechanism |
|---------|------|-------|-----------|
| Admin single sync | Admin clicks "Sync" on a user profile | 1 user | `POST /api/admin/sync/user/:id` |
| Admin bulk sync | Admin clicks "Refresh All" | All users | `POST /api/admin/sync/bulk` |
| First login | User logs in and `last_synced_at IS NULL` | 1 user | Middleware hook in auth flow |
| Stale login | User logs in and `last_synced_at < NOW() - TTL` | 1 user | Middleware hook in auth flow |

---

## 2. Implementation Plan

### Phase 1: Remove Scheduled Sync, Create On-Demand Triggers

**Goal:** Replace `APScheduler` interval jobs with explicit API-triggered sync.

#### Tasks

1. **Add new database models** -- `SyncJob` and `SyncJobItem` for audit tracking.
2. **Refactor `WorkdaySync`** -- Add `sync_single_worker(workday_id)` method that fetches one user + custom object data.
3. **Create sync orchestrator service** (`backend/app/services/sync_orchestrator.py`) that:
   - Validates requests
   - Creates `SyncJob` records
   - Delegates to `WorkdaySync` methods
   - Updates `SyncJob` with results
4. **Create admin sync routes** (`backend/app/routes/admin_sync.py`) with endpoints:
   - `POST /api/admin/sync/user/<workday_id>`
   - `POST /api/admin/sync/bulk`
   - `GET /api/admin/sync/status/<job_id>`
   - `GET /api/admin/sync/history`
5. **Remove `APScheduler` from `scheduler.py`** -- Keep module for backwards compatibility but remove interval jobs.
6. **Add first-login sync hook** -- In auth login route, check if user needs sync and trigger inline.

**Effort estimate:** 3-4 days

#### Files Changed

| File | Change |
|------|--------|
| `backend/app/models.py` | Add `SyncJob`, `SyncJobItem` models; add `last_synced_at`, `sync_status`, `sync_error` to `Worker` |
| `backend/app/services/workday_sync.py` | Add `sync_single_worker()`, `fetch_single_worker()` methods |
| `backend/app/services/sync_orchestrator.py` | **New** -- orchestration logic |
| `backend/app/routes/admin_sync.py` | **New** -- admin sync endpoints |
| `backend/app/services/scheduler.py` | Remove interval jobs; keep module stub |
| `backend/app/routes/auth.py` | Add first-login / stale-login sync hook |
| `backend/app/__init__.py` | Register `admin_sync` blueprint |
| `backend/config.py` | Add `SYNC_CACHE_TTL`, `SYNC_BULK_BATCH_SIZE`, `SYNC_RATE_LIMIT_PER_MINUTE` |

### Phase 2: Implement Caching Layer with TTL

**Goal:** Serve cached data efficiently with staleness awareness.

#### Tasks

1. **Add `last_synced_at` column** to `Worker` model (already partially present via `updated_at`, but add explicit sync timestamp).
2. **Add `sync_status` enum column** to `Worker` (`SYNCED`, `STALE`, `ERROR`, `NEVER_SYNCED`).
3. **Implement cache-aside read pattern** in `worker_to_dict()` -- include `is_stale` and `last_synced_at` in API responses.
4. **Add TTL check utility** -- `is_worker_stale(worker)` returns `True` if `last_synced_at < now - TTL`.
5. **Add migration script** for new columns.

**Effort estimate:** 1-2 days

### Phase 3: Graceful Degradation

**Goal:** When Workday is unreachable, serve cached data transparently.

#### Tasks

1. **Add circuit breaker** to `WorkdaySync` -- After N consecutive failures, stop attempting calls for a cooldown period.
2. **Return cached data with staleness metadata** -- Sync endpoints return `200` with cached data + warning header when Workday is down.
3. **Add health check endpoint** -- `GET /api/admin/sync/health` reports Workday reachability.
4. **Queue failed syncs for retry** -- Store failed sync requests in `SyncJob` with `RETRY` status; expose retry mechanism.

**Effort estimate:** 2-3 days

### Phase 4: Audit Logging

**Goal:** Full traceability for every sync operation.

#### Tasks

1. **Populate `SyncJob` records** with:
   - `initiated_by` (admin worker ID or `system/first-login`)
   - `trigger_type` (manual, bulk, first_login, stale_login)
   - `started_at`, `completed_at`
   - `status` (pending, running, completed, failed, partial)
   - `total_count`, `success_count`, `error_count`
2. **Populate `SyncJobItem` records** with:
   - `worker_id`, `workday_id`
   - `status` (synced, skipped, error)
   - `changed_fields` (JSON -- which fields actually changed)
   - `error_message`
3. **Build audit history endpoint** with filtering and pagination.

**Effort estimate:** 2 days

### Total Estimated Effort: 8-11 days

---

## 3. API Design for Sync Triggers

### 3.1 POST /api/admin/sync/user/{workday_id}

Sync a single user from Workday.

**Authorization:** Admin role required.

**Request:**

```http
POST /api/admin/sync/user/WD-12345
Content-Type: application/json
```

No request body required. The `workday_id` path parameter identifies the user.

**Response (200 -- Success):**

```json
{
  "job_id": "sync-abc-123",
  "status": "completed",
  "worker": {
    "id": 42,
    "workday_id": "WD-12345",
    "name": "Jane Smith",
    "email": "jane.smith@company.com",
    "table": "T-14",
    "team_name": "Team Alpha",
    "last_synced_at": "2026-02-13T10:30:00Z",
    "sync_status": "synced"
  },
  "changed_fields": ["table", "team_name"],
  "previous_values": {
    "table": "T-12",
    "team_name": "Team Beta"
  }
}
```

**Response (404 -- User Not Found in Workday):**

```json
{
  "error": "user_not_found_in_workday",
  "message": "Worker WD-12345 was not found in Workday.",
  "cached_data_available": true
}
```

**Response (503 -- Workday Unavailable):**

```json
{
  "error": "workday_unavailable",
  "message": "Using cached data (last updated 2 hours ago).",
  "worker": { "...cached worker data..." },
  "last_synced_at": "2026-02-13T08:30:00Z",
  "is_stale": true
}
```

### 3.2 POST /api/admin/sync/bulk

Trigger a bulk sync of all users (or a filtered subset).

**Authorization:** Admin role required.

**Request:**

```json
{
  "filter": {
    "team_name": "Team Alpha",
    "table": "T-14"
  },
  "force": false
}
```

- `filter` (optional): Limit sync to workers matching criteria. Omit to sync all.
- `force` (optional): If `true`, sync even if within TTL. Defaults to `false`.

**Response (202 -- Accepted):**

```json
{
  "job_id": "sync-bulk-456",
  "status": "running",
  "total_workers": 150,
  "estimated_duration_seconds": 45,
  "status_url": "/api/admin/sync/status/sync-bulk-456"
}
```

**Rate Limit (429):**

```json
{
  "error": "rate_limited",
  "message": "Bulk sync already in progress. Check status of job sync-bulk-400.",
  "retry_after_seconds": 30,
  "active_job_id": "sync-bulk-400"
}
```

### 3.3 GET /api/admin/sync/status/{job_id}

Check the status of an async sync job.

**Authorization:** Admin role required.

**Response (200):**

```json
{
  "job_id": "sync-bulk-456",
  "status": "running",
  "trigger_type": "bulk",
  "initiated_by": {
    "id": 1,
    "name": "Admin User"
  },
  "started_at": "2026-02-13T10:30:00Z",
  "completed_at": null,
  "progress": {
    "total": 150,
    "completed": 87,
    "succeeded": 85,
    "failed": 2,
    "skipped": 0,
    "percent_complete": 58
  },
  "errors": [
    {
      "workday_id": "WD-99999",
      "error": "User not found in Workday"
    },
    {
      "workday_id": "WD-88888",
      "error": "Custom object fetch timeout"
    }
  ]
}
```

### 3.4 GET /api/admin/sync/history

Audit log of all sync operations.

**Authorization:** Admin role required.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `per_page` | int | 25 | Items per page (max 100) |
| `trigger_type` | string | -- | Filter: `manual`, `bulk`, `first_login`, `stale_login` |
| `status` | string | -- | Filter: `completed`, `failed`, `partial`, `running` |
| `since` | ISO datetime | -- | Filter: jobs started after this time |

**Response (200):**

```json
{
  "history": [
    {
      "job_id": "sync-bulk-456",
      "trigger_type": "bulk",
      "initiated_by": "Admin User",
      "started_at": "2026-02-13T10:30:00Z",
      "completed_at": "2026-02-13T10:31:15Z",
      "duration_seconds": 75,
      "status": "completed",
      "total": 150,
      "succeeded": 148,
      "failed": 2,
      "skipped": 0
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 25,
    "total": 42,
    "pages": 2
  }
}
```

---

## 4. Caching Strategy

### 4.1 Cache-Aside Pattern

PostgreSQL serves as the cache layer. All reads go to PostgreSQL. Writes to the cache happen only via sync operations from Workday.

```
READ PATH:
  Client --> Flask API --> PostgreSQL (cache)
                              |
                              +--> Response includes last_synced_at + is_stale flag

SYNC PATH (write-through to cache):
  Trigger --> SyncOrchestrator --> Workday API --> PostgreSQL (update cache)
```

### 4.2 TTL Configuration

| Data Type | TTL | Rationale |
|-----------|-----|-----------|
| Worker identity (name, email) | 4 hours | Rarely changes; stale data is low-risk |
| Hackathon fields (table, team_name) | 1 hour | Changes during event setup; needs fresher data |
| Worker role (admin/expert/hacker) | N/A (app-managed) | Not synced from Workday; managed locally |

**Config values (`config.py`):**

```python
SYNC_CACHE_TTL_IDENTITY = int(os.environ.get('SYNC_CACHE_TTL_IDENTITY', 14400))  # 4 hours
SYNC_CACHE_TTL_HACKATHON = int(os.environ.get('SYNC_CACHE_TTL_HACKATHON', 3600))  # 1 hour
```

### 4.3 Staleness Detection

```python
# backend/app/services/cache_utils.py

from datetime import datetime, timedelta
from config import Config


def is_worker_stale(worker):
    """Check if a worker's cached data is stale."""
    if worker.last_synced_at is None:
        return True  # Never synced

    ttl = timedelta(seconds=Config.SYNC_CACHE_TTL_HACKATHON)
    return datetime.utcnow() - worker.last_synced_at > ttl


def staleness_info(worker):
    """Return staleness metadata for API responses."""
    if worker.last_synced_at is None:
        return {
            'is_stale': True,
            'last_synced_at': None,
            'staleness_message': 'Never synced from Workday'
        }

    stale = is_worker_stale(worker)
    age = datetime.utcnow() - worker.last_synced_at

    if age.total_seconds() < 60:
        age_str = 'just now'
    elif age.total_seconds() < 3600:
        age_str = f'{int(age.total_seconds() / 60)} minutes ago'
    else:
        age_str = f'{int(age.total_seconds() / 3600)} hours ago'

    return {
        'is_stale': stale,
        'last_synced_at': worker.last_synced_at.isoformat(),
        'staleness_message': f'Last synced {age_str}' if not stale else f'Data may be outdated (last synced {age_str})'
    }
```

### 4.4 Invalidation Rules

| Rule | Trigger | Action |
|------|---------|--------|
| Explicit sync | Admin triggers sync | Fetch from Workday, update cache, reset `last_synced_at` |
| TTL expiration | Read detects `last_synced_at` past TTL | Mark as stale in response; do NOT auto-sync on read |
| Bulk refresh | Admin triggers bulk | Re-sync all (or filtered) workers |
| First login | User logs in with `last_synced_at IS NULL` | Inline sync before completing login |

### 4.5 Updated `worker_to_dict` with Staleness

```python
def worker_to_dict(worker):
    """Convert worker model to dictionary with cache metadata."""
    from app.services.cache_utils import staleness_info

    data = {
        'id': worker.id,
        'workday_id': worker.workday_id,
        'name': worker.name,
        'email': worker.email,
        'employee_id': worker.employee_id,
        'department': worker.department,
        'job_title': worker.job_title,
        'manager': worker.manager,
        'table': worker.table,
        'team_name': worker.team_name,
        'tenant_url': worker.tenant_url,
        'company': worker.company,
        'role': worker.role.value,
        'is_active': worker.is_active,
        'created_at': worker.created_at.isoformat() if worker.created_at else None,
        'updated_at': worker.updated_at.isoformat() if worker.updated_at else None,
    }
    data.update(staleness_info(worker))
    return data
```

---

## 5. Error Handling Matrix

| # | Scenario | HTTP Status | System Behavior | User-Facing Message | Recovery |
|---|----------|-------------|-----------------|---------------------|----------|
| 1 | Workday API unreachable (timeout/5xx) | 503 | Serve cached data; log error; set worker `sync_status=STALE` | "Workday is temporarily unavailable. Showing cached data (last updated {age})." | Circuit breaker opens; manual retry via admin panel |
| 2 | Workday rate limit (429) | 429 | Queue sync job for retry with exponential backoff; return job ID | "Sync request queued due to rate limits. Track progress: {status_url}" | Auto-retry after backoff; admin can check status |
| 3 | Partial data returned | 200 (with warning) | Store available fields; set missing fields to `NULL` if not already set; flag in job item | "Some profile fields could not be retrieved from Workday." | Admin can re-trigger sync for affected user |
| 4 | User not found in Workday | 404 | Skip user; log in `SyncJobItem`; do NOT delete local record | "User {workday_id} was not found in Workday." | Admin investigates; may indicate terminated employee |
| 5 | OAuth token expired/invalid | 401 | Attempt one token refresh; if that fails, treat as Workday unavailable | (Internal -- not surfaced directly) | Token auto-refreshes; alert admin if persistent |
| 6 | Bulk sync already running | 429 | Reject with reference to active job | "A bulk sync is already in progress (job {id}). Please wait or check its status." | Wait for active job; or admin cancels |
| 7 | Database write failure | 500 | Rollback transaction; mark `SyncJob` as failed; log full error | "Sync completed from Workday but failed to save locally. Please retry." | Admin retries; investigate DB issues |
| 8 | Concurrent sync for same user | 409 | Acquire row-level lock; second request waits or returns existing job | "Sync already in progress for this user." | Wait for lock release; auto-resolves |
| 9 | Network partition during bulk | 206 | Commit successful items; mark remaining as failed; partial status | "Bulk sync partially completed ({n}/{total}). See job details." | Admin retries failed items |

### Circuit Breaker Parameters

```python
# config.py additions
SYNC_CIRCUIT_BREAKER_THRESHOLD = 5      # consecutive failures before opening
SYNC_CIRCUIT_BREAKER_COOLDOWN = 300     # seconds before attempting again (5 min)
```

```python
# backend/app/services/circuit_breaker.py

import time
import logging

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Simple circuit breaker for Workday API calls."""

    def __init__(self, failure_threshold=5, cooldown_seconds=300):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed = operational, open = blocking calls

    def can_proceed(self):
        """Check if a call should be attempted."""
        if self.state == 'closed':
            return True

        # Check if cooldown has elapsed
        if time.time() - self.last_failure_time >= self.cooldown_seconds:
            self.state = 'half-open'
            logger.info("Circuit breaker entering half-open state")
            return True

        return False

    def record_success(self):
        """Record a successful call."""
        self.failure_count = 0
        self.state = 'closed'

    def record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = 'open'
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures. "
                f"Cooldown: {self.cooldown_seconds}s"
            )

    @property
    def is_open(self):
        return self.state == 'open' and not self.can_proceed()
```

---

## 6. New Database Models

### 6.1 Worker Model Changes

Add columns to the existing `Worker` model:

```python
class WorkerSyncStatus(Enum):
    NEVER_SYNCED = "never_synced"
    SYNCED = "synced"
    STALE = "stale"
    ERROR = "error"


class Worker(db.Model, UserMixin):
    # ... existing columns ...

    # New sync-tracking columns
    last_synced_at = db.Column(db.DateTime, nullable=True)
    worker_sync_status = db.Column(
        db.Enum(WorkerSyncStatus),
        default=WorkerSyncStatus.NEVER_SYNCED,
        nullable=False
    )
    sync_error = db.Column(db.Text, nullable=True)
```

### 6.2 SyncJob Model

```python
class SyncJobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class SyncTriggerType(Enum):
    MANUAL = "manual"
    BULK = "bulk"
    FIRST_LOGIN = "first_login"
    STALE_LOGIN = "stale_login"


class SyncJob(db.Model):
    """Tracks every sync operation for audit purposes."""
    __tablename__ = 'sync_jobs'

    id = db.Column(db.String(36), primary_key=True)  # UUID
    trigger_type = db.Column(db.Enum(SyncTriggerType), nullable=False)
    initiated_by_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=True)

    status = db.Column(db.Enum(SyncJobStatus), default=SyncJobStatus.PENDING, nullable=False)
    started_at = db.Column(db.DateTime, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    total_count = db.Column(db.Integer, default=0)
    success_count = db.Column(db.Integer, default=0)
    error_count = db.Column(db.Integer, default=0)
    skip_count = db.Column(db.Integer, default=0)

    filter_criteria = db.Column(db.JSON, nullable=True)  # For filtered bulk syncs
    error_summary = db.Column(db.Text, nullable=True)

    # Relationships
    initiated_by = db.relationship('Worker', foreign_keys=[initiated_by_id])
    items = db.relationship('SyncJobItem', backref='job', lazy='dynamic')

    __table_args__ = (
        Index('idx_sync_job_status_started', 'status', 'started_at'),
        Index('idx_sync_job_trigger', 'trigger_type', 'started_at'),
    )


class SyncJobItem(db.Model):
    """Per-worker result within a sync job."""
    __tablename__ = 'sync_job_items'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(36), db.ForeignKey('sync_jobs.id'), nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=True)
    workday_id = db.Column(db.String(255), nullable=False)

    status = db.Column(db.String(20), nullable=False)  # synced, skipped, error
    changed_fields = db.Column(db.JSON, nullable=True)  # {"table": {"old": "T-12", "new": "T-14"}}
    error_message = db.Column(db.Text, nullable=True)

    synced_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_sync_item_job_status', 'job_id', 'status'),
    )
```

---

## 7. Sync Orchestrator Service

```python
# backend/app/services/sync_orchestrator.py

import uuid
import logging
import threading
from datetime import datetime
from app import db
from app.models import (
    Worker, SyncJob, SyncJobItem, SyncJobStatus,
    SyncTriggerType, WorkerSyncStatus
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
        """Sync a single user from Workday. Returns (job, worker) tuple."""

        # Check circuit breaker
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
            worker.worker_sync_status = WorkerSyncStatus.SYNCED
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
        """Start a bulk sync. Returns job immediately; processing is async."""
        global _active_bulk_job_id

        if not _bulk_sync_lock.acquire(blocking=False):
            return None, _active_bulk_job_id  # Already running

        try:
            # Determine workers to sync
            query = Worker.query
            if filter_criteria:
                if filter_criteria.get('team_name'):
                    query = query.filter_by(team_name=filter_criteria['team_name'])
                if filter_criteria.get('table'):
                    query = query.filter_by(table=filter_criteria['table'])

            workers = query.all()

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

            # Run bulk sync in background thread
            thread = threading.Thread(
                target=self._run_bulk_sync,
                args=(job.id, [w.workday_id for w in workers], force),
                daemon=True
            )
            thread.start()

            return job, None
        except Exception:
            _bulk_sync_lock.release()
            raise

    def _run_bulk_sync(self, job_id, workday_ids, force):
        """Background worker for bulk sync. Processes in batches."""
        global _active_bulk_job_id
        from flask import current_app

        # This runs in a background thread, needs app context
        # The caller must ensure app context is available
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
        finally:
            _active_bulk_job_id = None
            _bulk_sync_lock.release()

    def _fallback_cached(self, workday_id, reason):
        """Return cached data when Workday is unavailable."""
        worker = Worker.query.filter_by(workday_id=workday_id).first()
        if worker:
            worker.worker_sync_status = WorkerSyncStatus.STALE
            db.session.commit()
        return None, worker
```

---

## 8. Admin Sync Routes

```python
# backend/app/routes/admin_sync.py

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import SyncJob, SyncJobItem, Worker
from app.services.sync_orchestrator import SyncOrchestrator
from app import db

bp = Blueprint('admin_sync', __name__, url_prefix='/api/admin/sync')

orchestrator = SyncOrchestrator()


def require_admin(f):
    """Decorator to require admin role."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role.value != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


@bp.route('/user/<workday_id>', methods=['POST'])
@login_required
@require_admin
def sync_user(workday_id):
    """Sync a single user from Workday."""
    try:
        job, worker = orchestrator.sync_single_user(
            workday_id=workday_id,
            initiated_by_id=current_user.id
        )

        if job is None and worker is not None:
            # Fallback: Workday unavailable, returning cached data
            from app.routes.workers import worker_to_dict
            return jsonify({
                'error': 'workday_unavailable',
                'message': 'Using cached data.',
                'worker': worker_to_dict(worker),
                'is_stale': True
            }), 503

        from app.routes.workers import worker_to_dict

        # Get changed fields from job item
        item = SyncJobItem.query.filter_by(job_id=job.id).first()

        return jsonify({
            'job_id': job.id,
            'status': job.status.value,
            'worker': worker_to_dict(worker),
            'changed_fields': list(item.changed_fields.keys()) if item and item.changed_fields else [],
            'previous_values': {
                k: v['old'] for k, v in (item.changed_fields or {}).items()
            }
        }), 200

    except Exception as e:
        # Try to return cached data on failure
        worker = Worker.query.filter_by(workday_id=workday_id).first()
        if worker:
            from app.routes.workers import worker_to_dict
            return jsonify({
                'error': 'sync_failed',
                'message': str(e),
                'worker': worker_to_dict(worker),
                'is_stale': True
            }), 503
        return jsonify({'error': 'sync_failed', 'message': str(e)}), 500


@bp.route('/bulk', methods=['POST'])
@login_required
@require_admin
def sync_bulk():
    """Trigger a bulk sync."""
    data = request.get_json(silent=True) or {}
    filter_criteria = data.get('filter')
    force = data.get('force', False)

    job, active_job_id = orchestrator.sync_bulk(
        initiated_by_id=current_user.id,
        filter_criteria=filter_criteria,
        force=force
    )

    if job is None:
        return jsonify({
            'error': 'rate_limited',
            'message': f'Bulk sync already in progress (job {active_job_id}).',
            'active_job_id': active_job_id,
            'retry_after_seconds': 30
        }), 429

    return jsonify({
        'job_id': job.id,
        'status': job.status.value,
        'total_workers': job.total_count,
        'status_url': f'/api/admin/sync/status/{job.id}'
    }), 202


@bp.route('/status/<job_id>', methods=['GET'])
@login_required
@require_admin
def sync_status(job_id):
    """Check sync job status."""
    job = SyncJob.query.get_or_404(job_id)

    errors = []
    error_items = SyncJobItem.query.filter_by(job_id=job.id, status='error').all()
    for item in error_items:
        errors.append({
            'workday_id': item.workday_id,
            'error': item.error_message
        })

    completed = job.success_count + job.error_count + job.skip_count
    percent = int((completed / job.total_count * 100)) if job.total_count > 0 else 0

    return jsonify({
        'job_id': job.id,
        'status': job.status.value,
        'trigger_type': job.trigger_type.value,
        'initiated_by': {
            'id': job.initiated_by.id,
            'name': job.initiated_by.name
        } if job.initiated_by else None,
        'started_at': job.started_at.isoformat(),
        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
        'progress': {
            'total': job.total_count,
            'completed': completed,
            'succeeded': job.success_count,
            'failed': job.error_count,
            'skipped': job.skip_count,
            'percent_complete': percent
        },
        'errors': errors
    }), 200


@bp.route('/history', methods=['GET'])
@login_required
@require_admin
def sync_history():
    """Get sync audit history."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 25, type=int), 100)
    trigger_type = request.args.get('trigger_type')
    status = request.args.get('status')
    since = request.args.get('since')

    query = SyncJob.query

    if trigger_type:
        query = query.filter_by(trigger_type=trigger_type)
    if status:
        query = query.filter_by(status=status)
    if since:
        from datetime import datetime
        try:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            query = query.filter(SyncJob.started_at >= since_dt)
        except ValueError:
            pass

    query = query.order_by(SyncJob.started_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    history = []
    for job in pagination.items:
        duration = None
        if job.started_at and job.completed_at:
            duration = int((job.completed_at - job.started_at).total_seconds())

        history.append({
            'job_id': job.id,
            'trigger_type': job.trigger_type.value,
            'initiated_by': job.initiated_by.name if job.initiated_by else 'system',
            'started_at': job.started_at.isoformat(),
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'duration_seconds': duration,
            'status': job.status.value,
            'total': job.total_count,
            'succeeded': job.success_count,
            'failed': job.error_count,
            'skipped': job.skip_count
        })

    return jsonify({
        'history': history,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    }), 200
```

---

## 9. Admin UI Specification

### 9.1 Sync Dashboard Page (`/admin/sync`)

**Layout:**

```
+------------------------------------------------------------------+
| WORKDAY SYNC MANAGEMENT                         [Refresh All]     |
+------------------------------------------------------------------+
| STATUS BAR                                                        |
| Circuit Breaker: CLOSED (healthy)    Last Bulk Sync: 2h ago      |
| Active Jobs: 0                       Total Workers: 247           |
+------------------------------------------------------------------+
|                                                                    |
| SYNC HISTORY                                          [Filter v]  |
+--------+----------+----------+--------+-------+-----+-------+    |
| Job ID | Trigger  | Admin    | Status | Total | OK  | Err   |    |
+--------+----------+----------+--------+-------+-----+-------+    |
| ...456 | bulk     | Admin U. | done   | 150   | 148 | 2     |    |
| ...789 | manual   | Admin U. | done   | 1     | 1   | 0     |    |
| ...012 | login    | system   | done   | 1     | 1   | 0     |    |
+--------+----------+----------+--------+-------+-----+-------+    |
|                                           [< 1 2 3 >]            |
+------------------------------------------------------------------+
```

### 9.2 User Profile Sync Widget

On each user's profile page in the admin view:

```
+------------------------------------------+
| WORKDAY SYNC                              |
| Status: Synced                            |
| Last synced: 45 minutes ago               |
| [Sync Now]                                |
|                                           |
| Recent changes:                           |
| - table: T-12 --> T-14 (2h ago)          |
| - team_name: Beta --> Alpha (2h ago)      |
+------------------------------------------+
```

### 9.3 Bulk Sync Progress Modal

When bulk sync is triggered:

```
+------------------------------------------+
| BULK SYNC IN PROGRESS                     |
|                                           |
| [=========>              ] 58%            |
| 87 / 150 workers synced                  |
|                                           |
| Succeeded: 85                             |
| Failed: 2                                 |
| Remaining: 63                             |
|                                           |
| Errors:                                   |
| - WD-99999: User not found               |
| - WD-88888: Timeout                       |
|                                           |
|                           [Close]         |
+------------------------------------------+
```

### 9.4 Stale Data Indicator

On any page showing worker data, if `is_stale === true`:

```
+------------------------------------------+
| Jane Smith                                |
| Table: T-14  |  Team: Alpha              |
| [!] Data may be outdated (last synced     |
|     3 hours ago)  [Refresh]               |
+------------------------------------------+
```

The `[!]` indicator is a yellow/amber warning icon. The `[Refresh]` link triggers `POST /api/admin/sync/user/:id` (visible only to admins).

---

## 10. Test Cases

### TC-01: Successful Single User Sync

```
GIVEN a worker with workday_id "WD-12345" exists in PostgreSQL
  AND the worker's table is "T-12" in the local cache
  AND Workday reports the worker's table is "T-14"
WHEN an admin triggers POST /api/admin/sync/user/WD-12345
THEN the response status is 200
  AND the response body contains the updated worker with table "T-14"
  AND response.changed_fields includes "table"
  AND response.previous_values.table equals "T-12"
  AND the worker's last_synced_at is updated to approximately now
  AND the worker's worker_sync_status is "synced"
  AND a SyncJob record exists with status "completed" and success_count 1
  AND a SyncJobItem record exists with changed_fields including table change
```

### TC-02: Successful Bulk Sync

```
GIVEN 150 workers exist in PostgreSQL
  AND all 150 have corresponding records in Workday
WHEN an admin triggers POST /api/admin/sync/bulk with no filter
THEN the response status is 202
  AND the response body contains a job_id and status "running"
  AND the response body contains total_workers 150
WHEN the admin polls GET /api/admin/sync/status/{job_id} until complete
THEN the job status is "completed"
  AND progress.total is 150
  AND progress.succeeded is 150
  AND all workers have updated last_synced_at timestamps
```

### TC-03: Workday Unavailable -- Use Cache

```
GIVEN a worker with workday_id "WD-12345" exists in PostgreSQL
  AND the worker was last synced 3 hours ago
  AND Workday API is returning HTTP 500
WHEN an admin triggers POST /api/admin/sync/user/WD-12345
THEN the response status is 503
  AND the response body contains error "workday_unavailable"
  AND the response body contains the cached worker data
  AND response.is_stale is true
  AND the worker's worker_sync_status is set to "stale"
  AND a SyncJob record exists with status "failed"
```

### TC-04: Rate Limiting with Queued Retry

```
GIVEN a bulk sync job "sync-bulk-400" is currently running
WHEN an admin triggers POST /api/admin/sync/bulk
THEN the response status is 429
  AND the response body contains error "rate_limited"
  AND the response body contains active_job_id "sync-bulk-400"
  AND no new SyncJob record is created
```

### TC-05: Partial Data Handling

```
GIVEN a worker with workday_id "WD-12345" exists in PostgreSQL
  AND Workday returns the worker's core fields (name, email)
  AND Workday returns null/empty for custom object fields (table, team_name)
WHEN an admin triggers POST /api/admin/sync/user/WD-12345
THEN the response status is 200
  AND the worker's name and email are updated from Workday
  AND the worker's table and team_name retain their previous cached values
  AND the SyncJobItem records which fields were updated
```

### TC-06: Concurrent Sync Requests (Locking)

```
GIVEN a worker with workday_id "WD-12345" exists in PostgreSQL
WHEN two admins simultaneously trigger POST /api/admin/sync/user/WD-12345
THEN one request completes with status 200
  AND the other request either:
    - Waits for the first to complete and then returns the fresh data, OR
    - Returns 409 with message "Sync already in progress for this user"
  AND only one SyncJob is created for this workday_id at this timestamp
  AND the worker's final state is consistent (no partial writes)
```

### TC-07: Cache TTL Expiration

```
GIVEN a worker with workday_id "WD-12345" exists in PostgreSQL
  AND the worker's last_synced_at is 2 hours ago
  AND SYNC_CACHE_TTL_HACKATHON is set to 3600 seconds (1 hour)
WHEN the worker data is fetched via GET /api/workers/{id}
THEN the response includes is_stale: true
  AND the response includes staleness_message "Data may be outdated (last synced 2 hours ago)"
  AND no automatic sync is triggered (staleness is informational only)
```

### TC-08: Audit Log Creation

```
GIVEN an admin with id 1 triggers POST /api/admin/sync/user/WD-12345
  AND the sync completes successfully
WHEN the admin fetches GET /api/admin/sync/history
THEN the history contains a record with:
  - trigger_type: "manual"
  - initiated_by: "Admin User"
  - status: "completed"
  - total: 1, succeeded: 1, failed: 0
  AND the record has valid started_at and completed_at timestamps
  AND duration_seconds is a positive integer
```

### TC-09: First Login Sync

```
GIVEN a worker with workday_id "WD-12345" exists in PostgreSQL
  AND the worker's last_synced_at is NULL (never synced)
WHEN the worker logs in via POST /api/auth/login
THEN a sync is triggered automatically before the login response
  AND the worker's last_synced_at is updated
  AND a SyncJob record exists with trigger_type "first_login"
  AND the login response contains fresh worker data
```

### TC-10: Circuit Breaker Activation

```
GIVEN 5 consecutive Workday API calls have failed
WHEN an admin triggers POST /api/admin/sync/user/WD-12345
THEN the circuit breaker is in "open" state
  AND the request does NOT call Workday API
  AND the response status is 503
  AND cached data is returned with is_stale: true
WHEN 5 minutes (cooldown) have elapsed
  AND an admin triggers POST /api/admin/sync/user/WD-12345
THEN the circuit breaker is in "half-open" state
  AND one Workday API call is attempted
  AND if successful, the circuit breaker returns to "closed" state
```

---

## 11. Risks and Mitigations

| # | Risk | Probability | Impact | Mitigation |
|---|------|-------------|--------|------------|
| 1 | **Workday rate limiting during bulk sync** | High | High -- sync stalls, users see stale data | Batch requests (50 per batch), add 1s delay between batches, implement exponential backoff on 429 responses |
| 2 | **OAuth token expiration mid-bulk-sync** | Medium | Medium -- batch fails partway | Refresh token proactively before each batch; catch 401 and re-authenticate before retry |
| 3 | **Workday scheduled maintenance window** | Medium | Medium -- sync unavailable for hours | Circuit breaker prevents retry storms; cached data remains available; admin notified via health endpoint |
| 4 | **Data inconsistency during partial sync** | Medium | Medium -- some users updated, others stale | Each user update is atomic (committed individually within batch); SyncJob tracks partial completion; admin can re-run for failed items |
| 5 | **Concurrent admin bulk sync requests** | Low | Medium -- duplicate processing, DB contention | Mutex lock on bulk sync; second request gets 429 with reference to active job |
| 6 | **First-login sync adds latency to auth** | High | Low -- user waits 2-3 extra seconds | Set timeout on first-login sync (3s max); if timeout, proceed with cached data and mark stale; async sync in background |
| 7 | **Workday API response schema changes** | Low | High -- sync breaks silently | Validate response schema before processing; log warnings for unexpected fields; version the field mapping |
| 8 | **Thread safety of circuit breaker state** | Medium | Medium -- race conditions | Use `threading.Lock` for state transitions; or replace with Redis-backed circuit breaker if scaling beyond single process |
| 9 | **Background thread loses Flask app context** | High | High -- DB operations fail | Pass `app` reference to thread; wrap thread body in `with app.app_context():`; add error handling for context loss |
| 10 | **Stale cached data used for access control** | Low | High -- user gets wrong permissions | Worker `role` is app-managed, not synced from Workday; identity fields (name/email) are informational only; no security impact from staleness |

---

## 12. Migration Path from Current Implementation

### Step-by-step transition:

1. **Add new models and columns** (non-breaking DB migration)
   - Add `SyncJob`, `SyncJobItem` tables
   - Add `last_synced_at`, `worker_sync_status`, `sync_error` to `Worker`

2. **Deploy new sync service alongside old scheduler** (parallel operation)
   - New endpoints available but scheduler still running
   - Backfill `last_synced_at` from existing `updated_at` values

3. **Disable scheduler, enable on-demand** (feature flag)
   - Set `SYNC_MODE=on_demand` in config
   - Scheduler checks flag and skips if on-demand mode

4. **Remove scheduler code** (cleanup)
   - Delete `APScheduler` dependency
   - Remove `start_scheduler()` call from app init
   - Remove `WORKDAY_SYNC_INTERVAL` / `WORKDAY_TICKET_SYNC_INTERVAL` config

### Config changes:

```python
# Remove these:
# WORKDAY_SYNC_INTERVAL = int(os.environ.get('WORKDAY_SYNC_INTERVAL', 3600))
# WORKDAY_TICKET_SYNC_INTERVAL = int(os.environ.get('WORKDAY_TICKET_SYNC_INTERVAL', 300))

# Add these:
SYNC_CACHE_TTL_IDENTITY = int(os.environ.get('SYNC_CACHE_TTL_IDENTITY', 14400))
SYNC_CACHE_TTL_HACKATHON = int(os.environ.get('SYNC_CACHE_TTL_HACKATHON', 3600))
SYNC_BULK_BATCH_SIZE = int(os.environ.get('SYNC_BULK_BATCH_SIZE', 50))
SYNC_BULK_BATCH_DELAY = float(os.environ.get('SYNC_BULK_BATCH_DELAY', 1.0))
SYNC_CIRCUIT_BREAKER_THRESHOLD = int(os.environ.get('SYNC_CIRCUIT_BREAKER_THRESHOLD', 5))
SYNC_CIRCUIT_BREAKER_COOLDOWN = int(os.environ.get('SYNC_CIRCUIT_BREAKER_COOLDOWN', 300))
SYNC_FIRST_LOGIN_TIMEOUT = int(os.environ.get('SYNC_FIRST_LOGIN_TIMEOUT', 3))
```

---

## 13. File Index (New and Modified Files)

| File | Status | Purpose |
|------|--------|---------|
| `backend/app/models.py` | Modified | Add `WorkerSyncStatus`, `SyncJobStatus`, `SyncTriggerType` enums; `SyncJob`, `SyncJobItem` models; new Worker columns |
| `backend/app/services/sync_orchestrator.py` | New | Core sync orchestration logic |
| `backend/app/services/circuit_breaker.py` | New | Circuit breaker for Workday API resilience |
| `backend/app/services/cache_utils.py` | New | Staleness detection and cache metadata utilities |
| `backend/app/routes/admin_sync.py` | New | Admin sync API endpoints |
| `backend/app/routes/workers.py` | Modified | Update `worker_to_dict` with staleness info |
| `backend/app/routes/auth.py` | Modified | Add first-login sync hook |
| `backend/app/services/workday_sync.py` | Modified | Add `fetch_single_worker()` method |
| `backend/app/services/scheduler.py` | Modified | Remove interval jobs (or deprecate entirely) |
| `backend/app/__init__.py` | Modified | Register `admin_sync` blueprint |
| `backend/config.py` | Modified | Add new sync config values, remove old interval configs |
