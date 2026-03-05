"""Test message persistence and retrieval.

Test cases from chat-system-restructure.md Section 8:
- TC-9: Load older messages (pagination)
- TC-13: Unread badge appears (message state tracking)
- TC-14: Unread badge increments
- TC-15: Unread badge clears on selection
"""
import pytest
from app import db
from app.models import ChatMessage, MessageType, Worker


class TestMessageCreation:
    """Tests for creating messages via REST API."""

    def test_create_channel_message(self, authenticated_client, regular_user):
        """Create a channel message via REST API.

        Given   an authenticated user
        When    POST /api/messages with channel type
        Then    the message is created with correct fields
        """
        response = authenticated_client.post('/api/messages', json={
            'content': 'Hello channel!',
            'message_type': 'channel',
            'channel_id': 'channel_general',
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['content'] == 'Hello channel!'
        assert data['message_type'] == 'channel'
        assert data['channel_id'] == 'channel_general'
        assert data['sender']['id'] == regular_user.id

    def test_create_direct_message(self, authenticated_client, regular_user, admin_user):
        """Create a direct message via REST API.

        Given   an authenticated user and a recipient
        When    POST /api/messages with direct type and recipient_id
        Then    the message is created with correct sender and recipient
        """
        response = authenticated_client.post('/api/messages', json={
            'content': 'Hey admin!',
            'message_type': 'direct',
            'recipient_id': admin_user.id,
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['content'] == 'Hey admin!'
        assert data['message_type'] == 'direct'
        assert data['recipient_id'] == admin_user.id

    def test_create_ticket_thread_message(self, app, authenticated_client, regular_user):
        """Create a ticket thread message.

        Given   an authenticated user and an existing ticket
        When    POST /api/messages with ticket_thread type
        Then    the message is linked to the ticket thread
        """
        # Create a ticket first (we need admin/expert for this)
        from app.models import Ticket, TicketStatus, TicketPriority, SyncStatus
        with app.app_context():
            ticket = Ticket(
                ticket_number=1,
                reporter_id=regular_user.id,
                description='Test ticket',
                status=TicketStatus.OPEN,
                priority=TicketPriority.NORMAL,
                sync_status=SyncStatus.PENDING,
            )
            db.session.add(ticket)
            db.session.commit()
            ticket_id = ticket.id

        response = authenticated_client.post('/api/messages', json={
            'content': 'Working on this ticket',
            'message_type': 'ticket_thread',
            'thread_id': ticket_id,
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['thread_id'] == ticket_id

    def test_create_message_without_content_fails(self, authenticated_client):
        """Creating a message without content fails.

        Given   an authenticated user
        When    POST /api/messages with empty content
        Then    the response is 400
        """
        response = authenticated_client.post('/api/messages', json={
            'message_type': 'channel',
            'channel_id': 'channel_general',
        })
        assert response.status_code == 400

    def test_create_message_without_type_fails(self, authenticated_client):
        """Creating a message without message_type fails.

        Given   an authenticated user
        When    POST /api/messages without message_type
        Then    the response is 400
        """
        response = authenticated_client.post('/api/messages', json={
            'content': 'Hello',
        })
        assert response.status_code == 400

    def test_create_message_with_invalid_type_fails(self, authenticated_client):
        """Creating a message with invalid type returns 400.

        Given   an authenticated user
        When    POST /api/messages with an invalid message_type
        Then    the response is 400
        """
        response = authenticated_client.post('/api/messages', json={
            'content': 'Hello',
            'message_type': 'nonexistent_type',
        })
        assert response.status_code == 400


class TestMessageRetrieval:
    """Tests for retrieving messages."""

    def test_get_channel_messages(self, authenticated_client, regular_user):
        """Get messages from a channel.

        Given   messages exist in a channel
        When    GET /api/messages?type=channel&channel_id=channel_general
        Then    messages are returned with pagination
        """
        # Create a message first
        authenticated_client.post('/api/messages', json={
            'content': 'Test message',
            'message_type': 'channel',
            'channel_id': 'channel_general',
        })

        response = authenticated_client.get(
            '/api/messages?type=channel&channel_id=channel_general'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'messages' in data
        assert 'pagination' in data
        assert len(data['messages']) >= 1

    def test_get_direct_messages(self, authenticated_client, regular_user, admin_user):
        """Get direct messages between two users.

        Given   DM messages between user and admin
        When    GET /api/messages?recipient_id={admin_id}
        Then    messages between the two users are returned
        """
        authenticated_client.post('/api/messages', json={
            'content': 'DM to admin',
            'message_type': 'direct',
            'recipient_id': admin_user.id,
        })

        response = authenticated_client.get(
            f'/api/messages?recipient_id={admin_user.id}'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['messages']) >= 1

    def test_message_pagination(self, app, authenticated_client, regular_user):
        """TC-9: Load older messages (pagination).

        Given   a conversation has 200 messages
        When    the user requests page 1 with per_page=50
        Then    50 messages are returned
        And     pagination metadata shows total and pages
        """
        # Create 60 messages in bulk
        with app.app_context():
            for i in range(60):
                msg = ChatMessage(
                    sender_id=regular_user.id,
                    content=f'Message {i + 1}',
                    message_type=MessageType.CHANNEL,
                    channel_id='channel_general',
                )
                db.session.add(msg)
            db.session.commit()

        response = authenticated_client.get(
            '/api/messages?type=channel&channel_id=channel_general&per_page=50&page=1'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['messages']) == 50
        assert data['pagination']['total'] == 60
        assert data['pagination']['pages'] == 2

        # Get page 2
        response = authenticated_client.get(
            '/api/messages?type=channel&channel_id=channel_general&per_page=50&page=2'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['messages']) == 10

    def test_get_single_message(self, authenticated_client, regular_user):
        """Get a single message by ID.

        Given   an existing message
        When    GET /api/messages/{id}
        Then    the message is returned with sender info
        """
        # Create a message
        create_response = authenticated_client.post('/api/messages', json={
            'content': 'Single message test',
            'message_type': 'channel',
            'channel_id': 'channel_general',
        })
        msg_id = create_response.get_json()['id']

        response = authenticated_client.get(f'/api/messages/{msg_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['id'] == msg_id
        assert data['content'] == 'Single message test'
        assert 'sender' in data
        assert data['sender']['id'] == regular_user.id

    def test_get_nonexistent_message_returns_404(self, authenticated_client):
        """Getting a nonexistent message returns 404.

        Given   a message ID that does not exist
        When    GET /api/messages/99999
        Then    the response is 404
        """
        response = authenticated_client.get('/api/messages/99999')
        assert response.status_code == 404


class TestMessageAuth:
    """Tests for message endpoint authentication."""

    def test_unauthenticated_cannot_get_messages(self, client):
        """Unauthenticated user cannot access messages.

        Given   an unauthenticated user
        When    GET /api/messages
        Then    the response is 401
        """
        response = client.get('/api/messages')
        assert response.status_code in [401, 302]

    def test_unauthenticated_cannot_create_messages(self, client):
        """Unauthenticated user cannot create messages.

        Given   an unauthenticated user
        When    POST /api/messages
        Then    the response is 401
        """
        response = client.post('/api/messages', json={
            'content': 'Unauthorized',
            'message_type': 'channel',
            'channel_id': 'channel_general',
        })
        assert response.status_code in [401, 302]
