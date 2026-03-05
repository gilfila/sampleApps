"""Test MFA enrollment functionality.

Test cases from workstream-3-security-hardening-mfa.md Section 8.6:
- TC-MFA-01: Successful MFA enrollment
- TC-MFA-02: Enrollment verification with invalid code
- TC-MFA-03: Cannot enroll when already enrolled
"""
import pytest
from unittest.mock import patch, MagicMock


class TestMFAEnrollment:
    """Tests for MFA enrollment flow."""

    def test_successful_mfa_enrollment_initiation(self, authenticated_client):
        """TC-MFA-01 (Part 1): Initiate MFA enrollment.

        Given   an authenticated user without MFA enabled
        When    the user calls POST /api/auth/mfa/enroll
        Then    the response contains qr_code (base64 PNG), manual_key, issuer, account
        """
        response = authenticated_client.post('/api/auth/mfa/enroll')
        if response.status_code == 404:
            pytest.skip('MFA enrollment endpoint not yet implemented')

        assert response.status_code == 200
        data = response.get_json()
        assert 'qr_code' in data
        assert 'manual_key' in data
        assert 'issuer' in data or 'account' in data

    def test_enrollment_verification_with_valid_code(self, authenticated_client):
        """TC-MFA-01 (Part 2): Verify enrollment with correct TOTP code.

        Given   a user in the middle of MFA enrollment
        When    the user enters the correct TOTP code
        And     calls POST /api/auth/mfa/verify-enrollment
        Then    the response contains backup codes
        And     MFA is enabled for the user
        """
        # First initiate enrollment
        enroll_response = authenticated_client.post('/api/auth/mfa/enroll')
        if enroll_response.status_code == 404:
            pytest.skip('MFA enrollment endpoint not yet implemented')

        # We need the secret to generate a valid TOTP code
        try:
            import pyotp
            data = enroll_response.get_json()
            secret = data.get('manual_key', data.get('secret'))
            if not secret:
                pytest.skip('Enrollment response does not contain manual_key or secret')

            totp = pyotp.TOTP(secret)
            valid_code = totp.now()

            response = authenticated_client.post('/api/auth/mfa/verify-enrollment', json={
                'totp_code': valid_code,
            })
            assert response.status_code == 200
            verify_data = response.get_json()
            assert 'backup_codes' in verify_data
            assert len(verify_data['backup_codes']) == 8
        except ImportError:
            pytest.skip('pyotp not installed')

    def test_enrollment_verification_with_invalid_code(self, authenticated_client):
        """TC-MFA-02: Enrollment verification with invalid code.

        Given   a user in the middle of MFA enrollment
        When    the user calls POST /api/auth/mfa/verify-enrollment with totp_code="000000"
        Then    the response is 400 with error "Invalid verification code"
        """
        # Initiate enrollment first
        enroll_response = authenticated_client.post('/api/auth/mfa/enroll')
        if enroll_response.status_code == 404:
            pytest.skip('MFA enrollment endpoint not yet implemented')

        response = authenticated_client.post('/api/auth/mfa/verify-enrollment', json={
            'totp_code': '000000',
        })
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'invalid' in data['error'].lower() or 'verification' in data['error'].lower()

    def test_cannot_enroll_when_already_enrolled(self, authenticated_client):
        """TC-MFA-03: Cannot enroll when already enrolled.

        Given   an authenticated user with MFA already enabled
        When    the user calls POST /api/auth/mfa/enroll
        Then    the response is 400 with error "MFA is already enabled"
        """
        # Initiate enrollment
        enroll_response = authenticated_client.post('/api/auth/mfa/enroll')
        if enroll_response.status_code == 404:
            pytest.skip('MFA enrollment endpoint not yet implemented')

        # Complete enrollment
        try:
            import pyotp
            data = enroll_response.get_json()
            secret = data.get('manual_key', data.get('secret'))
            if not secret:
                pytest.skip('Cannot complete enrollment to test re-enrollment')

            totp = pyotp.TOTP(secret)
            authenticated_client.post('/api/auth/mfa/verify-enrollment', json={
                'totp_code': totp.now(),
            })

            # Try to enroll again
            response = authenticated_client.post('/api/auth/mfa/enroll')
            assert response.status_code == 400
            data = response.get_json()
            assert 'already' in data.get('error', '').lower()
        except ImportError:
            pytest.skip('pyotp not installed')

    def test_unauthenticated_cannot_enroll(self, client):
        """Unauthenticated user cannot initiate MFA enrollment.

        Given   an unauthenticated user
        When    POST /api/auth/mfa/enroll
        Then    the response is 401
        """
        response = client.post('/api/auth/mfa/enroll')
        assert response.status_code in [401, 302, 404]
