"""MFA API endpoints: enrollment, login verification, backup codes, admin management."""

from functools import wraps
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, make_response
from flask_login import login_required, login_user, current_user
from app import db, limiter
from app.models import Worker, UserMFA, TrustedDevice, MFAAuditLog, AppSetting
from app.utils.mfa import (
    generate_totp_secret, generate_qr_code, verify_totp_code,
    encrypt_secret, decrypt_secret,
    generate_mfa_token, verify_mfa_token,
    generate_backup_codes, hash_backup_code, verify_backup_code,
    generate_device_token, hash_device_token,
)
from app.utils.auth import verify_password

bp = Blueprint('mfa', __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _audit(user_id, action, details=None):
    """Write an MFA audit log entry."""
    entry = MFAAuditLog(
        user_id=user_id,
        action=action,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', '')[:500],
        details=details,
    )
    db.session.add(entry)


def _require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role.value != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


def _check_trusted_device(user):
    """Return True if the request carries a valid trusted-device cookie."""
    token = request.cookies.get('device_token')
    if not token:
        return False

    token_hash = hash_device_token(token)
    device = TrustedDevice.query.filter_by(
        user_id=user.id,
        device_token_hash=token_hash
    ).first()

    if not device:
        return False

    if device.expires_at < datetime.utcnow():
        db.session.delete(device)
        db.session.commit()
        return False

    device.last_used_at = datetime.utcnow()
    db.session.commit()
    return True


# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------

@bp.route('/api/auth/mfa/enroll', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def enroll():
    """Start MFA enrollment: generate TOTP secret and QR code."""
    existing = UserMFA.query.get(current_user.id)
    if existing and existing.is_enabled:
        return jsonify({'error': 'MFA is already enabled'}), 400

    secret = generate_totp_secret()
    ciphertext, nonce = encrypt_secret(secret)

    if existing:
        existing.totp_secret_encrypted = ciphertext
        existing.totp_secret_nonce = nonce
        existing.is_enabled = False
    else:
        mfa = UserMFA(
            user_id=current_user.id,
            totp_secret_encrypted=ciphertext,
            totp_secret_nonce=nonce,
            is_enabled=False,
        )
        db.session.add(mfa)

    db.session.commit()

    qr = generate_qr_code(secret, current_user.email)

    return jsonify({
        'qr_code': qr,
        'manual_key': secret,
        'issuer': 'HackathonApp',
        'account': current_user.email,
    }), 200


@bp.route('/api/auth/mfa/verify-enrollment', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def verify_enrollment():
    """Verify TOTP code to complete MFA enrollment."""
    data = request.get_json() or {}
    totp_code = data.get('totp_code')
    if not totp_code:
        return jsonify({'error': 'totp_code is required'}), 400

    mfa = UserMFA.query.get(current_user.id)
    if not mfa:
        return jsonify({'error': 'No pending enrollment found'}), 400
    if mfa.is_enabled:
        return jsonify({'error': 'MFA is already enabled'}), 400

    secret = decrypt_secret(mfa.totp_secret_encrypted, mfa.totp_secret_nonce)

    if not verify_totp_code(secret, totp_code):
        return jsonify({'error': 'Invalid verification code'}), 400

    # Generate backup codes
    codes = generate_backup_codes()
    mfa.backup_codes = [hash_backup_code(c) for c in codes]
    mfa.backup_codes_remaining = len(codes)
    mfa.is_enabled = True
    mfa.updated_at = datetime.utcnow()

    _audit(current_user.id, 'enrolled')
    db.session.commit()

    return jsonify({
        'message': 'MFA enabled successfully',
        'backup_codes': codes,
        'backup_codes_count': len(codes),
        'warning': 'Save these backup codes securely. They will not be shown again.',
    }), 200


# ---------------------------------------------------------------------------
# Login verification
# ---------------------------------------------------------------------------

@bp.route('/api/auth/mfa/verify-login', methods=['POST'])
@limiter.limit("5 per minute")
def verify_login():
    """Verify TOTP or backup code during login (after password step)."""
    data = request.get_json() or {}
    mfa_token = data.get('mfa_token')
    totp_code = data.get('totp_code')
    backup_code = data.get('backup_code')
    remember_device = data.get('remember_device', False)

    if not mfa_token:
        return jsonify({'error': 'mfa_token is required'}), 400

    user_id = verify_mfa_token(mfa_token)
    if user_id is None:
        return jsonify({'error': 'Invalid or expired MFA token. Please login again.'}), 401

    user = db.session.get(Worker, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    mfa = UserMFA.query.get(user_id)
    if not mfa or not mfa.is_enabled:
        return jsonify({'error': 'MFA is not enabled for this user'}), 400

    # -- TOTP verification --
    if totp_code:
        secret = decrypt_secret(mfa.totp_secret_encrypted, mfa.totp_secret_nonce)
        if not verify_totp_code(secret, totp_code):
            _audit(user_id, 'login_failed', {'reason': 'invalid_totp'})
            db.session.commit()
            return jsonify({'error': 'Invalid verification code'}), 400

        _audit(user_id, 'login_success', {'method': 'totp'})

    # -- Backup-code verification --
    elif backup_code:
        matched_idx = None
        for idx, stored_hash in enumerate(mfa.backup_codes):
            if verify_backup_code(backup_code, stored_hash):
                matched_idx = idx
                break

        if matched_idx is None:
            _audit(user_id, 'login_failed', {'reason': 'invalid_backup_code'})
            db.session.commit()
            return jsonify({'error': 'Invalid backup code'}), 400

        # Consume the code
        codes = list(mfa.backup_codes)
        codes.pop(matched_idx)
        mfa.backup_codes = codes
        mfa.backup_codes_remaining = len(codes)

        _audit(user_id, 'backup_code_used', {'remaining': len(codes)})
    else:
        return jsonify({'error': 'Either totp_code or backup_code is required'}), 400

    # Create full session
    login_user(user, remember=True)

    response_data = {
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'role': user.role.value,
        },
        'backup_codes_remaining': mfa.backup_codes_remaining,
    }

    if mfa.backup_codes_remaining == 0:
        response_data['warning'] = 'All backup codes have been used. Please generate new ones.'

    db.session.commit()

    resp = make_response(jsonify(response_data), 200)

    # Trusted-device cookie
    if remember_device:
        device_token = generate_device_token()
        device = TrustedDevice(
            user_id=user.id,
            device_token_hash=hash_device_token(device_token),
            user_agent=request.headers.get('User-Agent', '')[:500],
            ip_address=request.remote_addr,
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        db.session.add(device)
        db.session.commit()

        resp.set_cookie(
            'device_token',
            device_token,
            max_age=30 * 24 * 3600,
            httponly=True,
            secure=True,
            samesite='Lax',
        )

    return resp


# ---------------------------------------------------------------------------
# Backup codes management
# ---------------------------------------------------------------------------

@bp.route('/api/auth/mfa/backup-codes', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def regenerate_backup_codes():
    """Regenerate backup codes (invalidates old ones). Requires password."""
    data = request.get_json() or {}
    password = data.get('password')
    if not password:
        return jsonify({'error': 'Password is required'}), 400

    if not verify_password(password, current_user.password_hash):
        return jsonify({'error': 'Invalid password'}), 401

    mfa = UserMFA.query.get(current_user.id)
    if not mfa or not mfa.is_enabled:
        return jsonify({'error': 'MFA is not enabled'}), 400

    codes = generate_backup_codes()
    mfa.backup_codes = [hash_backup_code(c) for c in codes]
    mfa.backup_codes_remaining = len(codes)
    mfa.updated_at = datetime.utcnow()

    _audit(current_user.id, 'backup_codes_regenerated')
    db.session.commit()

    return jsonify({
        'backup_codes': codes,
        'backup_codes_count': len(codes),
        'warning': 'Previous backup codes have been invalidated.',
    }), 200


# ---------------------------------------------------------------------------
# Disable MFA
# ---------------------------------------------------------------------------

@bp.route('/api/auth/mfa/disable', methods=['DELETE'])
@login_required
@limiter.limit("5 per minute")
def disable_mfa():
    """Disable MFA. Requires password and current TOTP code."""
    data = request.get_json() or {}
    password = data.get('password')
    totp_code = data.get('totp_code')

    if not password or not totp_code:
        return jsonify({'error': 'Password and TOTP code are required'}), 400

    if not verify_password(password, current_user.password_hash):
        return jsonify({'error': 'Invalid password'}), 401

    mfa = UserMFA.query.get(current_user.id)
    if not mfa or not mfa.is_enabled:
        return jsonify({'error': 'MFA is not enabled'}), 400

    secret = decrypt_secret(mfa.totp_secret_encrypted, mfa.totp_secret_nonce)
    if not verify_totp_code(secret, totp_code):
        return jsonify({'error': 'Invalid TOTP code'}), 400

    # Remove MFA and trusted devices
    TrustedDevice.query.filter_by(user_id=current_user.id).delete()
    db.session.delete(mfa)

    _audit(current_user.id, 'disabled')
    db.session.commit()

    return jsonify({'message': 'MFA disabled successfully'}), 200


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

@bp.route('/api/admin/mfa/reset/<int:user_id>', methods=['POST'])
@login_required
@_require_admin
def admin_reset_mfa(user_id):
    """Admin resets a user's MFA (lockout recovery)."""
    user = db.session.get(Worker, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    mfa = UserMFA.query.get(user_id)
    if mfa:
        db.session.delete(mfa)
    TrustedDevice.query.filter_by(user_id=user_id).delete()

    _audit(user_id, 'admin_reset', {'admin_id': current_user.id})
    db.session.commit()

    return jsonify({
        'message': f'MFA reset for user {user_id}',
        'user_email': user.email,
    }), 200


@bp.route('/api/admin/mfa/status', methods=['GET'])
@login_required
@_require_admin
def admin_mfa_status():
    """View MFA enrollment statistics."""
    total_users = Worker.query.count()
    mfa_enabled = UserMFA.query.filter_by(is_enabled=True).count()
    trusted_devices = TrustedDevice.query.filter(
        TrustedDevice.expires_at > datetime.utcnow()
    ).count()
    recent_lockouts = MFAAuditLog.query.filter(
        MFAAuditLog.action == 'login_failed',
        MFAAuditLog.created_at >= datetime.utcnow() - timedelta(hours=24),
    ).count()

    enforcement_row = AppSetting.query.get('mfa_enforcement')
    enforcement = enforcement_row.value if enforcement_row else 'optional'

    return jsonify({
        'total_users': total_users,
        'mfa_enabled': mfa_enabled,
        'mfa_disabled': total_users - mfa_enabled,
        'enforcement': enforcement,
        'recent_lockouts': recent_lockouts,
        'trusted_devices': trusted_devices,
    }), 200


@bp.route('/api/admin/mfa/enforcement', methods=['PUT'])
@login_required
@_require_admin
def admin_mfa_enforcement():
    """Toggle MFA enforcement policy."""
    data = request.get_json() or {}
    policy = data.get('policy')
    valid_policies = ('optional', 'required_for_admins', 'required_for_all')

    if policy not in valid_policies:
        return jsonify({
            'error': f'Invalid policy. Must be one of: {", ".join(valid_policies)}'
        }), 400

    setting = AppSetting.query.get('mfa_enforcement')
    if setting:
        setting.value = policy
        setting.updated_by = current_user.id
        setting.updated_at = datetime.utcnow()
    else:
        setting = AppSetting(
            key='mfa_enforcement',
            value=policy,
            updated_by=current_user.id,
        )
        db.session.add(setting)

    db.session.commit()

    return jsonify({
        'message': 'MFA enforcement updated',
        'policy': policy,
    }), 200
