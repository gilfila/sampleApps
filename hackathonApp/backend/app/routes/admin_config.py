"""Admin configuration API (Workday integration, etc.)."""

from functools import wraps
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import AppSetting
from app.services.workday_config import (
    WORKDAY_CONFIG_KEY,
    get_workday_config,
    is_workday_configured,
    mask_secrets,
)
from app import db

bp = Blueprint("admin_config", __name__, url_prefix="/api/admin/config")


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role.value != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated


ALLOWED_WORKDAY_KEYS = {
    "tenant", "client_id", "client_secret", "refresh_token",
    "custom_object_name", "ticket_custom_object_name",
    "sync_interval", "ticket_sync_interval", "ticket_sync_retry_attempts",
}


@bp.route("/workday", methods=["GET"])
@login_required
@require_admin
def get_workday():
    """Get Workday integration config (secrets masked)."""
    config = get_workday_config()
    return jsonify({
        "configured": is_workday_configured(),
        "config": mask_secrets(config),
    }), 200


@bp.route("/workday", methods=["PUT"])
@login_required
@require_admin
def update_workday():
    """Update Workday integration config (in-app). Partial update supported."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON object required"}), 400

    # Only allow known keys
    updates = {k: v for k, v in data.items() if k in ALLOWED_WORKDAY_KEYS}
    if not updates:
        return jsonify({"error": "No valid Workday config keys provided"}), 400

    row = AppSetting.query.get(WORKDAY_CONFIG_KEY)
    if row and isinstance(row.value, dict):
        merged = dict(row.value)
    else:
        merged = {}
    merged.update(updates)
    # Coerce integers
    for key in ("sync_interval", "ticket_sync_interval", "ticket_sync_retry_attempts"):
        if key in merged and merged[key] is not None:
            try:
                merged[key] = int(merged[key])
            except (TypeError, ValueError):
                pass

    if row:
        row.value = merged
        row.updated_by = current_user.id
    else:
        row = AppSetting(key=WORKDAY_CONFIG_KEY, value=merged, updated_by=current_user.id)
        db.session.add(row)
    db.session.commit()

    return jsonify({
        "message": "Workday config updated",
        "configured": is_workday_configured(),
        "config": mask_secrets(get_workday_config()),
    }), 200
