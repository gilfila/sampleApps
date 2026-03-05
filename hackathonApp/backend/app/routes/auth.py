from flask import Blueprint, request, jsonify, make_response, session
from app import db
from app.models import Worker, WorkerRole, Channel, ChannelMember
from app.utils.auth import hash_password, verify_password
from flask_login import login_user, logout_user, login_required, current_user

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def _role_value(worker):
    """Safe role string for JSON; avoid AttributeError if role is None."""
    return (worker.role or WorkerRole.HACKER).value


@bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()

    email = data.get('email')
    password = data.get('password')
    name = data.get('name')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    # Check if user exists
    worker = Worker.query.filter_by(email=email).first()
    if not worker:
        return jsonify({'error': 'Email not found. Please contact admin.'}), 404

    # Check if already registered
    if worker.password_hash:
        return jsonify({'error': 'User already registered'}), 400

    # Set password
    worker.password_hash = hash_password(password)
    if name:
        worker.name = name

    # Add new user to default channels (Get-Help, General) if they exist
    for ch in Channel.query.filter(Channel.name.in_(('General', 'Get-Help'))).all():
        if not ChannelMember.query.filter_by(channel_id=ch.id, worker_id=worker.id).first():
            db.session.add(ChannelMember(channel_id=ch.id, worker_id=worker.id))

    db.session.commit()

    return jsonify({'message': 'Registration successful', 'user_id': worker.id}), 201


@bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json(silent=True) or {}
    except Exception:
        return jsonify({'error': 'Invalid request body'}), 400

    email = (data.get('email') or '').strip()
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    try:
        worker = Worker.query.filter_by(email=email).first()
    except Exception as e:
        return jsonify({'error': 'Database error. Run migrations: python database/run_migrations.py', 'detail': str(e)}), 500

    if not worker or not worker.password_hash:
        return jsonify({'error': 'Invalid credentials'}), 401

    if not verify_password(password, worker.password_hash):
        return jsonify({'error': 'Invalid credentials'}), 401

    if not worker.is_active:
        return jsonify({'error': 'Account is disabled'}), 403

    login_user(worker, remember=True)

    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': worker.id,
            'email': worker.email,
            'name': worker.name,
            'role': _role_value(worker)
        }
    }), 200


@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout user and clear trusted device cookie if present."""
    logout_user()
    resp = make_response(jsonify({'message': 'Logout successful'}), 200)
    resp.delete_cookie('device_token')
    return resp


@bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current user info"""
    return jsonify({
        'id': current_user.id,
        'email': current_user.email,
        'name': current_user.name,
        'role': _role_value(current_user),
        'table': current_user.table,
        'team_name': current_user.team_name,
        'company': current_user.company
    }), 200


@bp.route('/refresh', methods=['POST'])
@login_required
def refresh_session():
    """Refresh the current session to extend expiration."""
    session.modified = True  # Force session cookie refresh
    return jsonify({
        'message': 'Session refreshed',
        'user': {
            'id': current_user.id,
            'email': current_user.email,
            'name': current_user.name,
            'role': _role_value(current_user)
        }
    }), 200
