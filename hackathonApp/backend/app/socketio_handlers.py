"""WebSocket event handlers for real-time chat.

Supports both the new conversation-based messaging (channels & DMs) and
the legacy message_type-based flow so existing code keeps working.
"""

from app import socketio, db
from app.models import (
    ChatMessage, MessageType, Channel, ChannelMember, Conversation,
)
from app.services.seed_channels import GET_HELP_CHANNEL_NAME, get_system_worker
from app.services.agent import get_agent_reply
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room
from sqlalchemy import or_
from collections import defaultdict
from time import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# In-memory rate tracking for WebSocket messages (per-user)
_ws_rate_tracker = defaultdict(list)
WS_MSG_LIMIT = 50
WS_MSG_WINDOW = 60  # seconds


def check_ws_rate_limit(user_id):
    """Check if user has exceeded WebSocket message rate limit (50/min)."""
    now = time()
    _ws_rate_tracker[user_id] = [
        t for t in _ws_rate_tracker[user_id] if now - t < WS_MSG_WINDOW
    ]
    if len(_ws_rate_tracker[user_id]) >= WS_MSG_LIMIT:
        return False
    _ws_rate_tracker[user_id].append(now)
    return True


# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------

@socketio.on('connect')
def handle_connect(auth):
    """Handle client connection — auto-join all channel & DM rooms."""
    if not current_user.is_authenticated:
        return False

    logger.info(f"User {current_user.id} connected")

    # Join a personal room so we can push events to specific users
    join_room(f'user_{current_user.id}')

    # Auto-join all channels the user is a member of
    memberships = ChannelMember.query.filter_by(worker_id=current_user.id).all()
    for m in memberships:
        join_room(f'channel_{m.channel_id}')

    # Auto-join all DM conversation rooms
    convos = Conversation.query.filter(
        or_(
            Conversation.user_a_id == current_user.id,
            Conversation.user_b_id == current_user.id,
        )
    ).all()
    for c in convos:
        join_room(f'dm_{c.id}')

    emit('connected', {'user_id': current_user.id, 'message': 'Connected successfully'})


@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        logger.info(f"User {current_user.id} disconnected")


# ---------------------------------------------------------------------------
# Conversation-based messaging (new flow)
# ---------------------------------------------------------------------------

@socketio.on('join_conversation')
def handle_join_conversation(data):
    """Client tells us which conversation they are viewing."""
    if not current_user.is_authenticated:
        return False

    conversation_id = data.get('conversation_id')
    if conversation_id:
        join_room(conversation_id)
        logger.info(f"User {current_user.id} joined room {conversation_id}")
        emit('joined_room', {'room': conversation_id})


@socketio.on('send_message')
def handle_send_message(data):
    """Handle sending a message — supports conversation_id or legacy fields."""
    if not current_user.is_authenticated:
        emit('error', {'message': 'Not authenticated'})
        return False

    if not check_ws_rate_limit(current_user.id):
        emit('error', {'message': 'Rate limit exceeded. Max 50 messages per minute.'})
        return False

    content = (data.get('content') or '').strip()[:10000]
    conversation_id = data.get('conversation_id')

    if not content:
        emit('error', {'message': 'Message content is required'})
        return False

    # ------- New conversation-based flow -------
    if conversation_id:
        return _handle_conversation_message(content, conversation_id, data)

    # ------- Legacy flow (message_type + ids) -------
    return _handle_legacy_message(content, data)


def _handle_conversation_message(content, conversation_id, data):
    """Process a message targeted at a conversation_id (channel_X or dm_X)."""

    if conversation_id.startswith('channel_'):
        ch_db_id = int(conversation_id.replace('channel_', ''))
        channel = Channel.query.get(ch_db_id)
        if not channel:
            emit('error', {'message': 'Channel not found'})
            return False

        message = ChatMessage(
            sender_id=current_user.id,
            content=content,
            message_type=MessageType.CHANNEL,
            channel_id=str(ch_db_id),
            timestamp=datetime.utcnow(),
        )

    elif conversation_id.startswith('dm_'):
        dm_db_id = int(conversation_id.replace('dm_', ''))
        convo = Conversation.query.get(dm_db_id)
        if not convo:
            emit('error', {'message': 'Conversation not found'})
            return False

        # Determine recipient
        recipient_id = convo.user_b_id if convo.user_a_id == current_user.id else convo.user_a_id

        message = ChatMessage(
            sender_id=current_user.id,
            content=content,
            message_type=MessageType.DIRECT,
            recipient_id=recipient_id,
            timestamp=datetime.utcnow(),
        )
    else:
        emit('error', {'message': 'Invalid conversation ID'})
        return False

    db.session.add(message)
    db.session.commit()

    message_data = {
        'id': message.id,
        'sender': {
            'id': current_user.id,
            'name': current_user.name,
            'email': current_user.email,
        },
        'content': content,
        'message_type': message.message_type.value,
        'conversation_id': conversation_id,
        'timestamp': message.timestamp.isoformat(),
        'mentions': data.get('mentions', []),
    }

    # Broadcast to the room (everyone viewing that conversation)
    emit('new_message', message_data, room=conversation_id)
    logger.info(f"Message sent by user {current_user.id} to {conversation_id}")

    # Wire #Get-Help to agent: post an agent reply in the same channel
    if conversation_id.startswith('channel_') and channel.name == GET_HELP_CHANNEL_NAME:
        system_worker = get_system_worker()
        if system_worker:
            try:
                reply_text = get_agent_reply(content, user_id=current_user.id)
                agent_msg = ChatMessage(
                    sender_id=system_worker.id,
                    content=reply_text,
                    message_type=MessageType.CHANNEL,
                    channel_id=str(ch_db_id),
                    timestamp=datetime.utcnow(),
                )
                db.session.add(agent_msg)
                db.session.commit()
                agent_message_data = {
                    'id': agent_msg.id,
                    'sender': {
                        'id': system_worker.id,
                        'name': system_worker.name,
                        'email': system_worker.email,
                    },
                    'content': reply_text,
                    'message_type': MessageType.CHANNEL.value,
                    'conversation_id': conversation_id,
                    'timestamp': agent_msg.timestamp.isoformat(),
                    'mentions': [],
                }
                emit('new_message', agent_message_data, room=conversation_id)
            except Exception as e:
                logger.exception("Agent reply failed for Get-Help: %s", e)


def _handle_legacy_message(content, data):
    """Fallback for old-style messages with explicit message_type / channel_id / recipient_id."""
    message_type = data.get('message_type')
    thread_id = data.get('thread_id')
    channel_id = data.get('channel_id')
    group_id = data.get('group_id')
    recipient_id = data.get('recipient_id')

    if not message_type:
        emit('error', {'message': 'message_type or conversation_id is required'})
        return False

    try:
        msg_type = MessageType(message_type)
    except ValueError:
        emit('error', {'message': 'Invalid message type'})
        return False

    message = ChatMessage(
        sender_id=current_user.id,
        content=content,
        message_type=msg_type,
        thread_id=thread_id,
        channel_id=channel_id,
        group_id=group_id,
        recipient_id=recipient_id,
        timestamp=datetime.utcnow(),
    )
    db.session.add(message)
    db.session.commit()

    room = None
    if message_type == 'ticket_thread' and thread_id:
        room = f'ticket_{thread_id}'
    elif message_type == 'channel' and channel_id:
        room = f'channel_{channel_id}'
    elif message_type == 'group' and group_id:
        room = f'group_{group_id}'
    elif message_type == 'direct' and recipient_id:
        room = f'dm_{min(current_user.id, int(recipient_id))}_{max(current_user.id, int(recipient_id))}'

    message_data = {
        'id': message.id,
        'sender': {
            'id': current_user.id,
            'name': current_user.name,
            'email': current_user.email,
        },
        'content': content,
        'message_type': message_type,
        'thread_id': thread_id,
        'channel_id': channel_id,
        'group_id': group_id,
        'recipient_id': recipient_id,
        'timestamp': message.timestamp.isoformat(),
    }

    if room:
        emit('new_message', message_data, room=room)
    elif recipient_id:
        emit('new_message', message_data, room=f'user_{recipient_id}')

    emit('message_sent', message_data)
    logger.info(f"Legacy message sent by user {current_user.id}")


# ---------------------------------------------------------------------------
# Room management & typing (kept for backward compat + explicit join/leave)
# ---------------------------------------------------------------------------

@socketio.on('join_room')
def handle_join_room(data):
    if not current_user.is_authenticated:
        return False
    room = data.get('room')
    if room:
        join_room(room)
        emit('joined_room', {'room': room})


@socketio.on('leave_room')
def handle_leave_room(data):
    if not current_user.is_authenticated:
        return False
    room = data.get('room')
    if room:
        leave_room(room)
        emit('left_room', {'room': room})


@socketio.on('typing_indicator')
def handle_typing(data):
    if not current_user.is_authenticated:
        return False
    conversation_id = data.get('conversation_id')
    is_typing = data.get('is_typing', False)
    if conversation_id:
        emit('typing_indicator', {
            'conversation_id': conversation_id,
            'user_id': current_user.id,
            'user_name': current_user.name,
            'is_typing': is_typing,
        }, room=conversation_id, include_self=False)


@socketio.on('mark_read')
def handle_mark_read(data):
    """Stub — acknowledgement of read-receipts (future enhancement)."""
    if not current_user.is_authenticated:
        return False
    # No-op for now; the frontend already clears the badge client-side
    pass
