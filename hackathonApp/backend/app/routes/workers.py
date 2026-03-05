import os
import sys

from flask import Blueprint, request, jsonify
from app import db
from app.models import Worker, WorkerRole, ExpertAssignment
# from app.utils.sanitize import sanitize_search  # Optional sanitization
from flask_login import login_required, current_user
from datetime import datetime

bp = Blueprint('workers', __name__, url_prefix='/api/workers')

# Logan McNeil's Workday WID (for Worker Profile page)
LOGAN_WORKER_WID = "3aa5550b7fe348b98d7b5741afc65534"


def _get_workday_worker_profile(worker_id: str):
    """Call Workday via SOAP (Get_Workers) for the worker profile page. Returns dict or raises."""
    # __file__ is backend/app/routes/workers.py -> 3x dirname = backend, then parent = hackathon app root
    _backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    hackathon_root = os.path.dirname(_backend_root)
    workday_dir = os.path.join(hackathon_root, "workday_mcp_server")
    workday_env = os.path.join(workday_dir, ".env")
    if hackathon_root not in sys.path:
        sys.path.insert(0, hackathon_root)
    from dotenv import load_dotenv
    load_dotenv(workday_env, override=True)
    from workday_mcp_server import workday_auth, workday_soap
    token = workday_auth.get_workday_bearer_token()
    id_type = "WID" if len(worker_id.replace("-", "")) == 32 and worker_id.replace("-", "").isalnum() else "Employee_ID"
    return workday_soap.get_worker_via_soap(worker_id=worker_id, access_token=token, id_type=id_type)


@bp.route('/profile/<worker_id>', methods=['GET'])
@login_required
def get_worker_profile(worker_id):
    """Get a worker profile from Workday via SOAP (Get_Workers)."""
    try:
        data = _get_workday_worker_profile(worker_id)
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('', methods=['GET'])
@login_required
def get_workers():
    """Get all workers with optional filtering"""
    role = request.args.get('role')
    search = request.args.get('search')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    query = Worker.query

    if role:
        try:
            query = query.filter_by(role=WorkerRole(role))
        except ValueError:
            return jsonify({'error': 'Invalid role'}), 400

    if search:
        # Sanitize search input: escape LIKE wildcards to prevent LIKE-injection
        search = search.strip() if search else None
        query = query.filter(
            (Worker.name.ilike(f'%{search}%', escape='\\')) |
            (Worker.email.ilike(f'%{search}%', escape='\\'))
        )

    query = query.order_by(Worker.name)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    workers = pagination.items

    return jsonify({
        'workers': [worker_to_dict(w) for w in workers],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    }), 200


@bp.route('', methods=['POST'])
@login_required
def create_worker():
    """Create a worker (admin only). For local-only users omit workday_id or set to null."""
    if current_user.role.value != 'admin':
        return jsonify({'error': 'Only admins can create workers'}), 403

    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    name = (data.get('name') or '').strip()
    role_str = (data.get('role') or 'hacker').strip().lower()
    workday_id = data.get('workday_id')
    if workday_id is not None and workday_id != '':
        workday_id = str(workday_id).strip() or None
    else:
        workday_id = None

    if not email:
        return jsonify({'error': 'email is required'}), 400
    if not name:
        return jsonify({'error': 'name is required'}), 400

    try:
        role = WorkerRole(role_str)
    except ValueError:
        return jsonify({'error': 'Invalid role'}), 400

    if Worker.query.filter_by(email=email).first():
        return jsonify({'error': 'A worker with this email already exists'}), 409
    if workday_id and Worker.query.filter_by(workday_id=workday_id).first():
        return jsonify({'error': 'A worker with this workday_id already exists'}), 409

    worker = Worker(
        email=email,
        name=name,
        role=role,
        workday_id=workday_id,
    )
    db.session.add(worker)
    db.session.commit()

    return jsonify({'message': 'Worker created', 'worker': worker_to_dict(worker)}), 201


@bp.route('/<int:worker_id>', methods=['GET'])
@login_required
def get_worker(worker_id):
    """Get a specific worker"""
    worker = Worker.query.get_or_404(worker_id)
    return jsonify(worker_to_dict(worker)), 200


@bp.route('/<int:worker_id>', methods=['PATCH'])
@login_required
def update_worker(worker_id):
    """Update a worker (admin only). Only name, role, and is_active are updatable to avoid breaking refs."""
    if current_user.role.value != 'admin':
        return jsonify({'error': 'Only admins can update workers'}), 403

    worker = Worker.query.get_or_404(worker_id)
    data = request.get_json(silent=True) or {}

    if 'name' in data:
        name = (data.get('name') or '').strip()
        if name:
            worker.name = name
    if 'role' in data:
        role_str = (data.get('role') or '').strip().lower()
        try:
            worker.role = WorkerRole(role_str)
        except ValueError:
            return jsonify({'error': 'Invalid role'}), 400
    if 'is_active' in data:
        worker.is_active = bool(data.get('is_active'))

    db.session.commit()
    return jsonify({'message': 'Worker updated', 'worker': worker_to_dict(worker)}), 200


@bp.route('/<int:worker_id>/assign-expert', methods=['POST'])
@login_required
def assign_expert(worker_id):
    """Assign expert role to a worker (admin only)"""
    if current_user.role.value != 'admin':
        return jsonify({'error': 'Only admins can assign expert roles'}), 403

    worker = Worker.query.get_or_404(worker_id)

    # Check if already an expert
    if worker.role == WorkerRole.EXPERT:
        return jsonify({'error': 'Worker is already an expert'}), 400

    worker.role = WorkerRole.EXPERT

    # Create assignment record
    assignment = ExpertAssignment(
        worker_id=worker.id,
        assigned_by_id=current_user.id,
        assigned_at=datetime.utcnow()
    )

    db.session.add(assignment)
    db.session.commit()

    return jsonify({
        'message': 'Expert role assigned successfully',
        'worker': worker_to_dict(worker)
    }), 200


@bp.route('/<int:worker_id>/remove-expert', methods=['POST'])
@login_required
def remove_expert(worker_id):
    """Remove expert role from a worker (admin only)"""
    if current_user.role.value != 'admin':
        return jsonify({'error': 'Only admins can remove expert roles'}), 403

    worker = Worker.query.get_or_404(worker_id)

    if worker.role != WorkerRole.EXPERT:
        return jsonify({'error': 'Worker is not an expert'}), 400

    worker.role = WorkerRole.HACKER
    db.session.commit()

    return jsonify({
        'message': 'Expert role removed successfully',
        'worker': worker_to_dict(worker)
    }), 200


@bp.route('/sync-status', methods=['GET'])
@login_required
def get_sync_status():
    """Get Workday sync status (admin only). Works even when Workday not configured."""
    if current_user.role.value != 'admin':
        return jsonify({'error': 'Only admins can view sync status'}), 403

    from app.services.workday_config import is_workday_configured, get_workday_config
    configured = is_workday_configured()
    config = get_workday_config() if configured else {}
    return jsonify({
        'message': 'Sync status',
        'configured': configured,
        'worker_sync_interval': config.get('sync_interval', 3600) if configured else None,
    }), 200


@bp.route('/trigger-sync', methods=['POST'])
@login_required
def trigger_sync():
    """Trigger manual Workday worker sync (admin only). No-op when Workday not configured."""
    if current_user.role.value != 'admin':
        return jsonify({'error': 'Only admins can trigger sync'}), 403

    from app.services.workday_config import is_workday_configured
    if not is_workday_configured():
        return jsonify({
            'error': 'workday_not_configured',
            'message': 'Workday integration is not configured. Configure it in Administration.',
            'configured': False,
        }), 400

    from app.services.scheduler import sync_workers_job
    from flask import current_app

    try:
        import threading
        thread = threading.Thread(target=sync_workers_job, args=(current_app._get_current_object(),))
        thread.daemon = True
        thread.start()

        return jsonify({
            'message': 'Worker sync triggered successfully',
            'status': 'running',
            'configured': True,
        }), 200
    except Exception as e:
        return jsonify({
            'error': 'Failed to trigger sync',
            'details': str(e),
        }), 500


def worker_to_dict(worker):
    """Convert worker model to dictionary with cache staleness metadata."""
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
