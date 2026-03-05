"""Test rate limiting functionality.

Test cases from workstream-3-security-hardening-mfa.md Section 8.1:
- TC-RL-01: Login rate limit triggers after 5 attempts
- TC-RL-02: API rate limit triggers after 100 requests
- TC-RL-03: WebSocket rate limit triggers after 50 messages
- TC-RL-04: Rate limits are per-IP for unauthenticated endpoints
"""
import pytest


class TestLoginRateLimit:
    """Tests for login endpoint rate limiting."""

    def test_login_rate_limit_triggers_after_5_attempts(self, client, regular_user):
        """TC-RL-01: Login rate limit triggers after 5 attempts.

        Given   a user at IP 10.0.0.1
        When    the user sends 6 POST requests to /api/auth/login within 60 seconds
        Then    the first 5 requests return 200 or 401 (based on credentials)
        And     the 6th request returns 429 with rate limit error
        """
        for i in range(5):
            response = client.post('/api/auth/login', json={
                'email': 'user@test.com',
                'password': 'wrongpassword',
            })
            assert response.status_code in [200, 401], (
                f'Attempt {i + 1} should not be rate limited, got {response.status_code}'
            )

        # 6th attempt should be rate limited
        response = client.post('/api/auth/login', json={
            'email': 'user@test.com',
            'password': 'wrongpassword',
        })
        assert response.status_code == 429
        data = response.get_json()
        assert 'error' in data
        assert 'rate limit' in data['error'].lower() or 'rate_limit' in data.get('error', '').lower()

    def test_successful_login_counts_toward_rate_limit(self, client, regular_user):
        """Successful logins also count toward the rate limit budget.

        Given   a user who has logged in 5 times successfully
        When    the user attempts a 6th login
        Then    the 6th attempt is rate limited
        """
        for i in range(5):
            response = client.post('/api/auth/login', json={
                'email': 'user@test.com',
                'password': 'userpass',
            })
            assert response.status_code == 200, f'Login {i + 1} should succeed'

        response = client.post('/api/auth/login', json={
            'email': 'user@test.com',
            'password': 'userpass',
        })
        assert response.status_code == 429

    def test_rate_limit_response_includes_retry_after(self, client, regular_user):
        """Rate limit response includes retry_after information.

        Given   a rate-limited user
        When    the user receives a 429 response
        Then    the response body includes retry_after seconds
        """
        # Exhaust rate limit
        for _ in range(6):
            client.post('/api/auth/login', json={
                'email': 'user@test.com',
                'password': 'wrongpassword',
            })

        response = client.post('/api/auth/login', json={
            'email': 'user@test.com',
            'password': 'wrongpassword',
        })
        assert response.status_code == 429
        data = response.get_json()
        assert 'retry_after' in data or 'Retry-After' in response.headers


class TestAPIRateLimit:
    """Tests for authenticated API rate limiting."""

    def test_api_rate_limit_triggers_after_100_requests(self, authenticated_client):
        """TC-RL-02: API rate limit triggers after 100 requests.

        Given   an authenticated user
        When    the user sends 101 GET requests to /api/tickets within 1 hour
        Then    the first 100 requests return 200
        And     the 101st request returns 429
        """
        for i in range(100):
            response = authenticated_client.get('/api/tickets')
            assert response.status_code == 200, (
                f'Request {i + 1} should not be rate limited, got {response.status_code}'
            )

        response = authenticated_client.get('/api/tickets')
        assert response.status_code == 429


class TestRateLimitPerIP:
    """Tests for per-IP rate limiting on unauthenticated endpoints."""

    def test_rate_limits_are_per_ip(self, app, regular_user):
        """TC-RL-04: Rate limits are per-IP for unauthenticated endpoints.

        Given   two users at different IPs
        When    user A sends 5 login attempts and user B sends 5 login attempts
        Then    both users can complete their 5 attempts (not sharing a limit)
        """
        # Simulate two different IPs via separate clients with different headers
        client_a = app.test_client()
        client_b = app.test_client()

        # User A at IP 10.0.0.1: all 5 should work
        for i in range(5):
            response = client_a.post(
                '/api/auth/login',
                json={'email': 'user@test.com', 'password': 'wrong'},
                headers={'X-Forwarded-For': '10.0.0.1'},
            )
            assert response.status_code in [200, 401], (
                f'Client A attempt {i + 1} should not be rate limited'
            )

        # User B at IP 10.0.0.2: all 5 should also work
        for i in range(5):
            response = client_b.post(
                '/api/auth/login',
                json={'email': 'user@test.com', 'password': 'wrong'},
                headers={'X-Forwarded-For': '10.0.0.2'},
            )
            assert response.status_code in [200, 401], (
                f'Client B attempt {i + 1} should not be rate limited'
            )


class TestRegisterRateLimit:
    """Tests for registration endpoint rate limiting."""

    def test_register_rate_limit_triggers_after_3_attempts(self, client, regular_user):
        """Registration endpoint has a stricter rate limit of 3 per minute.

        Given   a user at a single IP
        When    4 POST requests are sent to /api/auth/register
        Then    the first 3 return non-429 responses
        And     the 4th returns 429
        """
        for i in range(3):
            response = client.post('/api/auth/register', json={
                'email': f'newuser{i}@test.com',
                'password': 'somepassword',
            })
            # 404 is expected because the email is not in Workday
            assert response.status_code in [201, 400, 404], (
                f'Register attempt {i + 1} should not be rate limited, got {response.status_code}'
            )

        response = client.post('/api/auth/register', json={
            'email': 'newuser99@test.com',
            'password': 'somepassword',
        })
        assert response.status_code == 429
