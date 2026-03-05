"""Test presence tracking functionality.

Test cases from chat-system-restructure.md Section 8.3:
- TC-10: User comes online
- TC-11: User goes offline
- TC-12: Initial online users list
"""
import pytest
from app import socketio


@pytest.fixture
def socketio_user_a(app, regular_user):
    """Create SocketIO test client for user A (regular_user)."""
    flask_client = app.test_client()
    flask_client.post('/api/auth/login', json={
        'email': 'user@test.com',
        'password': 'userpass',
    })
    sio_client = socketio.test_client(app, flask_test_client=flask_client)
    yield sio_client
    if sio_client.is_connected():
        sio_client.disconnect()


@pytest.fixture
def socketio_user_b(app, admin_user):
    """Create SocketIO test client for user B (admin_user)."""
    flask_client = app.test_client()
    flask_client.post('/api/auth/login', json={
        'email': 'admin@test.com',
        'password': 'adminpass',
    })
    sio_client = socketio.test_client(app, flask_test_client=flask_client)
    yield sio_client
    if sio_client.is_connected():
        sio_client.disconnect()


class TestPresenceOnline:
    """Tests for user coming online."""

    def test_user_connects_emits_connected(self, socketio_user_a):
        """TC-10: User comes online -- connected event.

        Given   User A connects to WebSocket
        Then    User A receives a 'connected' event
        """
        received = socketio_user_a.get_received()
        event_names = [r['name'] for r in received]
        assert 'connected' in event_names

    def test_connected_event_contains_user_id(self, socketio_user_a, regular_user):
        """Connected event contains the user's ID.

        Given   User A connects
        Then    the 'connected' event payload includes user_id
        """
        received = socketio_user_a.get_received()
        connected_events = [r for r in received if r['name'] == 'connected']
        assert len(connected_events) > 0
        assert connected_events[0]['args'][0]['user_id'] == regular_user.id


class TestPresenceOffline:
    """Tests for user going offline."""

    def test_user_disconnect_is_clean(self, socketio_user_a):
        """TC-11: User goes offline -- clean disconnect.

        Given   User A is connected
        When    User A disconnects
        Then    the disconnection completes without error
        """
        assert socketio_user_a.is_connected()
        socketio_user_a.disconnect()
        assert not socketio_user_a.is_connected()


class TestPresenceInitialList:
    """Tests for initial online users list."""

    def test_multiple_users_can_connect(self, socketio_user_a, socketio_user_b):
        """TC-12: Multiple users can be online simultaneously.

        Given   User A is already connected
        When    User B also connects
        Then    both users are connected
        """
        assert socketio_user_a.is_connected()
        assert socketio_user_b.is_connected()

    def test_users_receive_independent_connected_events(
        self, socketio_user_a, socketio_user_b, regular_user, admin_user
    ):
        """Each user receives their own connected event.

        Given   User A and User B both connect
        Then    User A's connected event has User A's ID
        And     User B's connected event has User B's ID
        """
        received_a = socketio_user_a.get_received()
        received_b = socketio_user_b.get_received()

        connected_a = [r for r in received_a if r['name'] == 'connected']
        connected_b = [r for r in received_b if r['name'] == 'connected']

        assert len(connected_a) > 0
        assert connected_a[0]['args'][0]['user_id'] == regular_user.id

        assert len(connected_b) > 0
        assert connected_b[0]['args'][0]['user_id'] == admin_user.id
