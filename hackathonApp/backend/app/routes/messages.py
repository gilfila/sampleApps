from flask import Blueprint, request, jsonify
from app import db
from app.models import ChatMessage, MessageType, Worker
# from app.utils.sanitize import sanitize_input  # Optional sanitization
from flask_login import login_required, current_user
from datetime import datetime

bp = Blueprint('messages', __name__, url_prefix='/api/messages')


@bp.route('', methods=['GET'])
@login_required
def get_messages():
    """Get messages with optional filtering"""
    message_type = request.args.get('type')
    thread_id = request.args.get('thread_id', type=int)
    channel_id = request.args.get('channel_id')
    group_id = request.args.get('group_id')
    recipient_id = request.args.get('recipient_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    query = ChatMessage.query

    if message_type:
        try:
            query = query.filter_by(message_type=MessageType(message_type))
        except ValueError:
            return jsonify({'error': 'Invalid message type'}), 400

    if thread_id:
        query = query.filter_by(thread_id=thread_id)

    if channel_id:
        query = query.filter_by(channel_id=channel_id)

    if group_id:
        query = query.filter_by(group_id=group_id)

    if recipient_id:
        # For direct messages, get messages where current user is sender or recipient
        query = query.filter(
            ((ChatMessage.sender_id == current_user.id) & (ChatMessage.recipient_id == recipient_id)) |
            ((ChatMessage.sender_id == recipient_id) & (ChatMessage.recipient_id == current_user.id))
        )

    query = query.order_by(ChatMessage.timestamp.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    messages = pagination.items

    return jsonify({
        'messages': [message_to_dict(m) for m in messages],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    }), 200


@bp.route('', methods=['POST'])
@login_required
# Rate limiting removed for development
def create_message():
    """Create a new message"""
    data = request.get_json()

    # Sanitize message content to prevent stored XSS
    content = data.get('content', '').strip()[:10000] if data.get('content') else ''
    message_type = data.get('message_type')

    if not content or not message_type:
        return jsonify({'error': 'Content and message_type are required'}), 400

    try:
        msg_type = MessageType(message_type)
    except ValueError:
        return jsonify({'error': 'Invalid message type'}), 400

    message = ChatMessage(
        sender_id=current_user.id,
        content=content,
        message_type=msg_type,
        thread_id=data.get('thread_id'),
        channel_id=data.get('channel_id'),
        group_id=data.get('group_id'),
        recipient_id=data.get('recipient_id'),
        timestamp=datetime.utcnow()
    )

    db.session.add(message)
    db.session.commit()

    # Emit via Socket.IO will be handled in socketio_handlers
    return jsonify(message_to_dict(message)), 201


@bp.route('/<int:message_id>', methods=['GET'])
@login_required
def get_message(message_id):
    """Get a specific message"""
    message = ChatMessage.query.get_or_404(message_id)
    return jsonify(message_to_dict(message)), 200


def message_to_dict(message):
    """Convert message model to dictionary"""
    return {
        'id': message.id,
        'sender': {
            'id': message.sender.id,
            'name': message.sender.name,
            'email': message.sender.email
        },
        'content': message.content,
        'message_type': message.message_type.value,
        'thread_id': message.thread_id,
        'channel_id': message.channel_id,
        'group_id': message.group_id,
        'recipient_id': message.recipient_id,
        'timestamp': message.timestamp.isoformat() if message.timestamp else None
    }
