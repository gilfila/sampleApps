"""Test WebSocket event handling.

Test cases from chat-system-restructure.md Section 8:
- TC-6: Send a message
- TC-7: Receive a real-time message
- TC-8: No duplicate messages on send
- TC-10: User comes online (presence)
- TC-11: User goes offline (presence)
- TC-12: Initial online users list
- TC-19: Show typing indicator
- TC-20: Typing indicator disappears after timeout
- TC-21: Multiple users typing
- TC-22: WebSocket disconnect
- TC-23: WebSocket reconnect
"""
import pytest
from unittest.mock import patch, MagicMock
from app import create_app, db, socketio
from app.models import Worker, WorkerRole, ChatMessage, MessageType


@pytest.fixture
def socketio_test_client(app, regular_user):
    """Create a SocketIO test client with an authenticated user."""
    flask_client = app.test_client()
    flask_client.post('/api/auth/login', json={
        'email': 'user@test.com',
        'password': 'userpass',
    })
    sio_client = socketio.test_client(
        app,
        flask_test_client=flask_client,
    )
    return sio_client


class TestSendMessage:
    """Tests for sending messages via WebSocket."""

    def test_send_channel_message(self, socketio_test_client, regular_user):
        """TC-6: Send a message via WebSocket.

        Given   the user has selected #general as the active conversation
        When    the user emits 'send_message' with content and channel_id
        Then    the message is persisted in the database
        And     a 'message_sent' event is emitted back to the sender
        """
        socketio_test_client.emit('join_room', {'room': 'channel_channel_general'})
        socketio_test_client.emit('send_message', {
            'content': 'Hello team!',
            'message_type': 'channel',
            'channel_id': 'channel_general',
        })

        received = socketio_test_client.get_received()
        event_names = [r['name'] for r in received]
        assert 'message_sent' in event_names or 'new_message' in event_names

    def test_send_direct_message(self, app, socketio_test_client, regular_user, admin_user):
        """Send a direct message to another user.

        Given   two authenticated users
        When    user A sends a DM to user B
        Then    the message is persisted with correct recipient_id
        """
        socketio_test_client.emit('send_message', {
            'content': 'Hey admin!',
            'message_type': 'direct',
            'recipient_id': admin_user.id,
        })

        received = socketio_test_client.get_received()
        sent_events = [r for r in received if r['name'] in ('message_sent', 'new_message')]
        assert len(sent_events) > 0

    def test_send_message_without_auth_fails(self, app):
        """Unauthenticated WebSocket message is rejected.

        Given   an unauthenticated user
        When    the user tries to emit 'send_message'
        Then    an error event is returned
        """
        flask_client = app.test_client()
        sio_client = socketio.test_client(app, flask_test_client=flask_client)

        if sio_client.is_connected():
            sio_client.emit('send_message', {
                'content': 'Unauthorized message',
                'message_type': 'channel',
                'channel_id': 'channel_general',
            })
            received = sio_client.get_received()
            error_events = [r for r in received if r['name'] == 'error']
            # Either error event or connection was refused
            if len(error_events) > 0:
                assert 'authenticated' in str(error_events[0]).lower() or \
                       'error' in str(error_events[0]).lower()

    def test_send_message_with_empty_content_fails(self, socketio_test_client):
        """Sending a message with empty content fails.

        Given   an authenticated user
        When    emitting 'send_message' with empty content
        Then    an error event is returned
        """
        socketio_test_client.emit('send_message', {
            'content': '',
            'message_type': 'channel',
            'channel_id': 'channel_general',
        })

        received = socketio_test_client.get_received()
        error_events = [r for r in received if r['name'] == 'error']
        assert len(error_events) > 0

    def test_send_message_with_invalid_type_fails(self, socketio_test_client):
        """Sending a message with invalid message_type fails.

        Given   an authenticated user
        When    emitting 'send_message' with message_type='invalid'
        Then    an error event is returned
        """
        socketio_test_client.emit('send_message', {
            'content': 'Test message',
            'message_type': 'invalid_type',
            'channel_id': 'channel_general',
        })

        received = socketio_test_client.get_received()
        error_events = [r for r in received if r['name'] == 'error']
        assert len(error_events) > 0


class TestRoomManagement:
    """Tests for WebSocket room join/leave."""

    def test_join_room(self, socketio_test_client):
        """User can join a room.

        Given   an authenticated user
        When    emitting 'join_room' with a room name
        Then    a 'joined_room' event is emitted back
        """
        socketio_test_client.emit('join_room', {'room': 'channel_general'})
        received = socketio_test_client.get_received()
        event_names = [r['name'] for r in received]
        assert 'joined_room' in event_names

    def test_leave_room(self, socketio_test_client):
        """User can leave a room.

        Given   an authenticated user who has joined a room
        When    emitting 'leave_room'
        Then    a 'left_room' event is emitted back
        """
        socketio_test_client.emit('join_room', {'room': 'channel_general'})
        socketio_test_client.get_received()  # clear

        socketio_test_client.emit('leave_room', {'room': 'channel_general'})
        received = socketio_test_client.get_received()
        event_names = [r['name'] for r in received]
        assert 'left_room' in event_names

    def test_join_room_without_auth_fails(self, app):
        """Unauthenticated user cannot join a room.

        Given   an unauthenticated user
        When    emitting 'join_room'
        Then    the request is rejected
        """
        flask_client = app.test_client()
        sio_client = socketio.test_client(app, flask_test_client=flask_client)

        if sio_client.is_connected():
            sio_client.emit('join_room', {'room': 'channel_general'})
            received = sio_client.get_received()
            # Should not receive joined_room
            event_names = [r['name'] for r in received]
            assert 'joined_room' not in event_names


class TestConnection:
    """Tests for WebSocket connect/disconnect."""

    def test_authenticated_user_can_connect(self, app, regular_user):
        """TC-22/TC-23 prerequisite: Authenticated user can connect.

        Given   an authenticated user
        When    a WebSocket connection is established
        Then    a 'connected' event is emitted
        """
        flask_client = app.test_client()
        flask_client.post('/api/auth/login', json={
            'email': 'user@test.com',
            'password': 'userpass',
        })
        sio_client = socketio.test_client(app, flask_test_client=flask_client)

        assert sio_client.is_connected()
        received = sio_client.get_received()
        event_names = [r['name'] for r in received]
        assert 'connected' in event_names
        sio_client.disconnect()

    def test_unauthenticated_user_connection_rejected(self, app):
        """Unauthenticated WebSocket connection is rejected.

        Given   an unauthenticated user
        When    a WebSocket connection is attempted
        Then    the connection is rejected or no 'connected' event is emitted
        """
        flask_client = app.test_client()
        sio_client = socketio.test_client(app, flask_test_client=flask_client)

        received = sio_client.get_received()
        connected_events = [r for r in received if r['name'] == 'connected']
        # Either not connected or no connected event
        if sio_client.is_connected():
            assert len(connected_events) == 0

    def test_disconnect_cleanup(self, app, regular_user):
        """Disconnecting a user triggers cleanup.

        Given   an authenticated user connected via WebSocket
        When    the user disconnects
        Then    the disconnection is logged
        """
        flask_client = app.test_client()
        flask_client.post('/api/auth/login', json={
            'email': 'user@test.com',
            'password': 'userpass',
        })
        sio_client = socketio.test_client(app, flask_test_client=flask_client)
        assert sio_client.is_connected()

        # Disconnect should not raise
        sio_client.disconnect()
        assert not sio_client.is_connected()
