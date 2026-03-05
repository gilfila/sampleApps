"""Chat API — channels, direct messages, conversation messages, and user search.

Endpoints:
    GET   /api/chats/channels                 – list channels the user belongs to (+ public ones)
    POST  /api/chats/channels                 – create a channel
    POST  /api/chats/channels/<id>/join       – join a public channel
    GET   /api/chats/direct-messages           – list DM conversations for the current user
    POST  /api/chats/direct-messages           – get-or-create a DM conversation
    GET   /api/chats/<conversation_id>/messages – paginated messages for a channel or DM
    GET   /api/chats/users/search              – fuzzy search hackathon participants
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_
from datetime import datetime

from app import db
from app.models import (
    Channel, ChannelType, ChannelMember,
    Conversation, ChatMessage, MessageType, Worker,
)

bp = Blueprint('chats', __name__, url_prefix='/api/chats')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _channel_to_dict(channel, member_count=None):
    return {
        'id': f'channel_{channel.id}',
        'db_id': channel.id,
        'name': channel.name,
        'description': channel.description or '',
        'channel_type': channel.channel_type.value,
        'created_by': {
            'id': channel.created_by.id,
            'name': channel.created_by.name,
        } if channel.created_by else None,
        'member_count': member_count if member_count is not None else channel.members.count(),
        'created_at': channel.created_at.isoformat() if channel.created_at else None,
    }


def _conversation_to_dict(convo, current_user_id):
    """Return a dict for a DM conversation, including the *other* user's info."""
    if convo.user_a_id == current_user_id:
        other = convo.user_b
    else:
        other = convo.user_a

    return {
        'id': f'dm_{convo.id}',
        'db_id': convo.id,
        'type': 'dm',
        'other_user': {
            'id': other.id,
            'name': other.name,
            'email': other.email,
        } if other else None,
        'created_at': convo.created_at.isoformat() if convo.created_at else None,
    }


def _message_to_dict(msg):
    return {
        'id': msg.id,
        'sender': {
            'id': msg.sender.id,
            'name': msg.sender.name,
            'email': msg.sender.email,
        } if msg.sender else None,
        'content': msg.content,
        'message_type': msg.message_type.value,
        'timestamp': msg.timestamp.isoformat() if msg.timestamp else None,
        'conversation_id': msg.channel_id,  # will be overridden below
    }


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------

@bp.route('/channels', methods=['GET'])
@login_required
def list_channels():
    """Return all public channels + any private channels the user is a member of."""
    # Public channels
    public = Channel.query.filter_by(channel_type=ChannelType.PUBLIC).all()

    # Private channels the user belongs to
    private_ids = (
        db.session.query(ChannelMember.channel_id)
        .filter(ChannelMember.worker_id == current_user.id)
        .subquery()
    )
    private = (
        Channel.query
        .filter(Channel.channel_type == ChannelType.PRIVATE)
        .filter(Channel.id.in_(private_ids))
        .all()
    )

    seen_ids = set()
    channels = []
    for ch in public + private:
        if ch.id not in seen_ids:
            seen_ids.add(ch.id)
            channels.append(_channel_to_dict(ch))

    return jsonify({'channels': channels}), 200


@bp.route('/channels', methods=['POST'])
@login_required
def create_channel():
    """Create a new channel. Creator is auto-joined."""
    data = request.get_json() or {}
    name = (data.get('name') or '').strip().lower().replace(' ', '-')
    description = (data.get('description') or '').strip()[:500]
    channel_type_str = data.get('channel_type', 'public')

    if not name or len(name) < 2 or len(name) > 80:
        return jsonify({'error': 'Channel name must be 2–80 characters'}), 400

    # Only allow alphanumeric + dashes
    if not all(c.isalnum() or c == '-' for c in name):
        return jsonify({'error': 'Channel name can only contain letters, numbers, and dashes'}), 400

    if Channel.query.filter_by(name=name).first():
        return jsonify({'error': 'A channel with that name already exists'}), 409

    try:
        ch_type = ChannelType(channel_type_str)
    except ValueError:
        ch_type = ChannelType.PUBLIC

    channel = Channel(
        name=name,
        description=description,
        channel_type=ch_type,
        created_by_id=current_user.id,
    )
    db.session.add(channel)
    db.session.flush()  # get channel.id

    # Auto-join creator
    member = ChannelMember(channel_id=channel.id, worker_id=current_user.id)
    db.session.add(member)
    db.session.commit()

    return jsonify({'channel': _channel_to_dict(channel)}), 201


@bp.route('/channels/<int:channel_id>/join', methods=['POST'])
@login_required
def join_channel(channel_id):
    """Join a public channel (or a private channel if invited — not yet implemented)."""
    channel = Channel.query.get_or_404(channel_id)

    if channel.channel_type == ChannelType.PRIVATE:
        # For now, only allow joining if already a member (invite flow TBD)
        existing = ChannelMember.query.filter_by(
            channel_id=channel.id, worker_id=current_user.id
        ).first()
        if not existing:
            return jsonify({'error': 'This is a private channel'}), 403

    existing = ChannelMember.query.filter_by(
        channel_id=channel.id, worker_id=current_user.id
    ).first()
    if not existing:
        db.session.add(ChannelMember(channel_id=channel.id, worker_id=current_user.id))
        db.session.commit()

    return jsonify({'channel': _channel_to_dict(channel)}), 200


# ---------------------------------------------------------------------------
# Direct Messages
# ---------------------------------------------------------------------------

@bp.route('/direct-messages', methods=['GET'])
@login_required
def list_direct_messages():
    """Return all DM conversations for the current user."""
    conversations = Conversation.query.filter(
        or_(
            Conversation.user_a_id == current_user.id,
            Conversation.user_b_id == current_user.id,
        )
    ).order_by(Conversation.created_at.desc()).all()

    return jsonify({
        'conversations': [_conversation_to_dict(c, current_user.id) for c in conversations],
    }), 200


@bp.route('/direct-messages', methods=['POST'])
@login_required
def get_or_create_dm():
    """Get or create a DM conversation between the current user and a target user."""
    data = request.get_json() or {}
    target_user_id = data.get('target_user_id')

    if not target_user_id:
        return jsonify({'error': 'target_user_id is required'}), 400

    target_user_id = int(target_user_id)

    if target_user_id == current_user.id:
        return jsonify({'error': 'Cannot DM yourself'}), 400

    target = Worker.query.get(target_user_id)
    if not target:
        return jsonify({'error': 'User not found'}), 404

    # Canonical ordering
    a_id = min(current_user.id, target_user_id)
    b_id = max(current_user.id, target_user_id)

    convo = Conversation.query.filter_by(user_a_id=a_id, user_b_id=b_id).first()
    if not convo:
        convo = Conversation(user_a_id=a_id, user_b_id=b_id)
        db.session.add(convo)
        db.session.commit()

    return jsonify({'conversation': _conversation_to_dict(convo, current_user.id)}), 200


# ---------------------------------------------------------------------------
# Messages (for both channels and DMs)
# ---------------------------------------------------------------------------

@bp.route('/<conversation_id>/messages', methods=['GET'])
@login_required
def get_conversation_messages(conversation_id):
    """Paginated messages for a channel or DM.

    conversation_id format:
        channel_<id>   → Channel messages
        dm_<id>        → DM conversation messages
    """
    before = request.args.get('before', type=int)
    limit = min(request.args.get('limit', 50, type=int), 100)

    query = ChatMessage.query

    if conversation_id.startswith('channel_'):
        ch_id = conversation_id.replace('channel_', '')
        query = query.filter(
            ChatMessage.message_type == MessageType.CHANNEL,
            ChatMessage.channel_id == ch_id,
        )
    elif conversation_id.startswith('dm_'):
        dm_id = int(conversation_id.replace('dm_', ''))
        convo = Conversation.query.get(dm_id)
        if not convo:
            return jsonify({'error': 'Conversation not found'}), 404
        # Both sides of the DM
        query = query.filter(
            ChatMessage.message_type == MessageType.DIRECT,
            or_(
                (ChatMessage.sender_id == convo.user_a_id) & (ChatMessage.recipient_id == convo.user_b_id),
                (ChatMessage.sender_id == convo.user_b_id) & (ChatMessage.recipient_id == convo.user_a_id),
            ),
        )
    else:
        return jsonify({'error': 'Invalid conversation ID format'}), 400

    if before:
        query = query.filter(ChatMessage.id < before)

    messages = query.order_by(ChatMessage.timestamp.desc()).limit(limit + 1).all()
    has_more = len(messages) > limit
    messages = messages[:limit]
    messages.reverse()  # oldest → newest

    result = []
    for m in messages:
        d = _message_to_dict(m)
        d['conversation_id'] = conversation_id
        result.append(d)

    return jsonify({'messages': result, 'has_more': has_more}), 200


# ---------------------------------------------------------------------------
# User Search (for starting new DMs)
# ---------------------------------------------------------------------------

@bp.route('/users/search', methods=['GET'])
@login_required
def search_users():
    """Fuzzy-search hackathon participants by name or email.

    Query params:
        q       – search term (min 1 char)
        limit   – max results (default 15)
    """
    q = (request.args.get('q') or '').strip()
    limit = min(request.args.get('limit', 15, type=int), 50)

    if len(q) < 1:
        return jsonify({'users': []}), 200

    results = (
        Worker.query
        .filter(
            Worker.is_active == True,  # noqa: E712
            Worker.id != current_user.id,
            or_(
                Worker.name.ilike(f'%{q}%'),
                Worker.email.ilike(f'%{q}%'),
            ),
        )
        .order_by(Worker.name)
        .limit(limit)
        .all()
    )

    users = [
        {
            'id': w.id,
            'name': w.name,
            'email': w.email,
            'role': w.role.value,
            'team_name': w.team_name,
        }
        for w in results
    ]

    return jsonify({'users': users}), 200
