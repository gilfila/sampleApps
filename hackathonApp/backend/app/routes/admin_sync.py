"""Admin sync API endpoints for Workday ad-hoc sync management. Require Workday to be configured."""

from functools import wraps
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import SyncJob, SyncJobItem, Worker
from app.services.sync_orchestrator import SyncOrchestrator
from app.services.workday_config import is_workday_configured
from app import db

bp = Blueprint('admin_sync', __name__, url_prefix='/api/admin/sync')

orchestrator = SyncOrchestrator()


def require_workday_configured(f):
    """Return 400 with message when Workday is not configured."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_workday_configured():
            return jsonify({
                'error': 'workday_not_configured',
                'message': 'Workday integration is not configured. Configure it in Administration / Configuration.'
            }), 400
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role.value != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


@bp.route('/user/<workday_id>', methods=['POST'])
@login_required
@require_admin
@require_workday_configured
def sync_user(workday_id):
    """Sync a single user from Workday."""
    try:
        job, worker = orchestrator.sync_single_user(
            workday_id=workday_id,
            initiated_by_id=current_user.id
        )

        if job is None and worker is not None:
            from app.routes.workers import worker_to_dict
            return jsonify({
                'error': 'workday_unavailable',
                'message': 'Using cached data.',
                'worker': worker_to_dict(worker),
                'is_stale': True
            }), 503

        from app.routes.workers import worker_to_dict

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
@require_workday_configured
def sync_bulk():
    """Trigger a bulk sync of all (or filtered) workers."""
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
    """Get sync audit history with pagination and filtering."""
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
