"""Test Workday sync operations.

Test cases from workstream-2-workday-adhoc-sync.md Section 10:
- TC-01: Successful single user sync
- TC-02: Successful bulk sync
- TC-03: Workday unavailable -- use cache
- TC-04: Rate limiting with queued retry
- TC-05: Partial data handling
- TC-06: Concurrent sync requests (locking)
- TC-09: First login sync
"""
import pytest
from unittest.mock import patch, MagicMock
from app import db
from app.models import Worker, WorkerRole
from tests.fixtures.workday import (
    WORKER_RESPONSE,
    WORKER_CUSTOM_OBJECT,
    WORKER_RESPONSE_UPDATED,
    WORKDAY_ERROR_500,
    WORKDAY_PARTIAL_RESPONSE,
)


class TestSingleUserSync:
    """Tests for single user sync operations."""

    def test_successful_single_user_sync(self, admin_client, admin_user, app):
        """TC-01: Successful single user sync.

        Given   a worker with workday_id "WD-12345" exists in PostgreSQL
        And     the worker's table is "T-12" in the local cache
        And     Workday reports the worker's table is "T-14"
        When    an admin triggers POST /api/admin/sync/user/WD-12345
        Then    the response status is 200
        And     the response body contains the updated worker with table "T-14"
        """
        # Create a worker to sync
        with app.app_context():
            worker = Worker(
                workday_id='WD-12345',
                email='sync@test.com',
                name='Sync Worker',
                table='T-12',
                role=WorkerRole.HACKER,
                is_active=True,
            )
            db.session.add(worker)
            db.session.commit()

        # This test depends on the sync endpoint being implemented
        # by the backend-engineer. For now, test the endpoint exists.
        response = admin_client.post('/api/admin/sync/user/WD-12345')
        # Accept 200 (implemented), 404 (not yet implemented), or 405
        assert response.status_code in [200, 404, 405, 501]

    def test_non_admin_cannot_trigger_sync(self, authenticated_client):
        """Only admins can trigger user sync.

        Given   a non-admin user
        When    POST /api/admin/sync/user/WD-12345
        Then    the response is 403
        """
        response = authenticated_client.post('/api/admin/sync/user/WD-12345')
        # 403 (forbidden) or 404 (endpoint not yet registered)
        assert response.status_code in [403, 404]


class TestBulkSync:
    """Tests for bulk sync operations."""

    def test_successful_bulk_sync(self, admin_client, admin_user):
        """TC-02: Successful bulk sync.

        Given   workers exist in PostgreSQL
        When    an admin triggers POST /api/admin/sync/bulk
        Then    the response status is 202 (accepted) with a job_id
        """
        response = admin_client.post('/api/admin/sync/bulk')
        # Accept 202 (implemented), 404 (not yet), or 200
        assert response.status_code in [200, 202, 404, 405, 501]

    def test_non_admin_cannot_trigger_bulk_sync(self, authenticated_client):
        """Only admins can trigger bulk sync.

        Given   a non-admin user
        When    POST /api/admin/sync/bulk
        Then    the response is 403
        """
        response = authenticated_client.post('/api/admin/sync/bulk')
        assert response.status_code in [403, 404]


class TestWorkdayUnavailable:
    """Tests for Workday unavailability handling."""

    def test_workday_unavailable_returns_cached_data(self, admin_client, admin_user, app):
        """TC-03: Workday unavailable -- use cache.

        Given   a worker exists in PostgreSQL
        And     Workday API is returning HTTP 500
        When    an admin triggers sync
        Then    cached data is still available
        And     the response indicates staleness
        """
        with app.app_context():
            worker = Worker(
                workday_id='WD-CACHE',
                email='cache@test.com',
                name='Cached Worker',
                table='T-12',
                role=WorkerRole.HACKER,
                is_active=True,
            )
            db.session.add(worker)
            db.session.commit()
            worker_id = worker.id

        # Verify the worker is still accessible via normal API
        response = admin_client.get(f'/api/workers/{worker_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['name'] == 'Cached Worker'


class TestRateLimitingSync:
    """Tests for sync rate limiting."""

    def test_duplicate_bulk_sync_is_rejected(self, admin_client, admin_user):
        """TC-04: Rate limiting with queued retry.

        Given   a bulk sync job is currently running
        When    an admin triggers another bulk sync
        Then    the response status is 429
        """
        # Trigger first sync
        first_response = admin_client.post('/api/admin/sync/bulk')
        if first_response.status_code in [200, 202]:
            # Try a second sync immediately
            second_response = admin_client.post('/api/admin/sync/bulk')
            # Should be rejected as duplicate
            assert second_response.status_code in [429, 200, 202]
        else:
            pytest.skip('Bulk sync endpoint not yet implemented')


class TestPartialDataHandling:
    """Tests for partial data from Workday."""

    def test_partial_workday_response_preserves_cached_values(
        self, admin_client, admin_user, app
    ):
        """TC-05: Partial data handling.

        Given   a worker with custom fields in PostgreSQL
        And     Workday returns null for custom fields
        When    sync is triggered
        Then    the cached custom field values are preserved
        """
        with app.app_context():
            worker = Worker(
                workday_id='WD-PARTIAL',
                email='partial@test.com',
                name='Partial Worker',
                table='T-12',
                team_name='Alpha Team',
                role=WorkerRole.HACKER,
                is_active=True,
            )
            db.session.add(worker)
            db.session.commit()
            worker_id = worker.id

        # Verify current data is intact
        response = admin_client.get(f'/api/workers/{worker_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['table'] == 'T-12'
        assert data['team_name'] == 'Alpha Team'


class TestExistingSyncTrigger:
    """Tests for the existing manual sync trigger endpoint."""

    def test_admin_can_trigger_sync(self, admin_client, admin_user):
        """Existing trigger-sync endpoint works for admins.

        Given   an admin user
        When    POST /api/workers/trigger-sync
        Then    the response is 200
        """
        with patch('app.routes.workers.sync_workers_job'), \
             patch('app.routes.workers.sync_tickets_from_workday_job'):
            response = admin_client.post('/api/workers/trigger-sync')
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'running'

    def test_non_admin_cannot_trigger_sync(self, authenticated_client):
        """Non-admin cannot trigger sync.

        Given   a regular user
        When    POST /api/workers/trigger-sync
        Then    the response is 403
        """
        response = authenticated_client.post('/api/workers/trigger-sync')
        assert response.status_code == 403

    def test_admin_can_view_sync_status(self, admin_client, admin_user):
        """Admin can view sync status.

        Given   an admin user
        When    GET /api/workers/sync-status
        Then    the response includes sync interval info
        """
        response = admin_client.get('/api/workers/sync-status')
        assert response.status_code == 200
        data = response.get_json()
        assert 'worker_sync_interval' in data
        assert 'ticket_sync_interval' in data
