"""Agent API — chat endpoint for Cursor CLI and in-app agent.

POST /api/agent/chat — send a message and get an agent reply (same logic as #Get-Help wire).
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from app.services.agent import get_agent_reply

bp = Blueprint('agent', __name__, url_prefix='/api/agent')


@bp.route('/chat', methods=['POST'])
@login_required
def chat():
    """
    Send a message to the agent and receive a reply.
    Used by the in-app agent UI and by Cursor CLI (when configured to call this backend).
    """
    data = request.get_json() or {}
    message = (data.get('message') or '').strip()
    if not message:
        return jsonify({'error': 'message is required'}), 400
    reply = get_agent_reply(message, user_id=current_user.id, context=data.get('context'))
    return jsonify({'reply': reply}), 200
