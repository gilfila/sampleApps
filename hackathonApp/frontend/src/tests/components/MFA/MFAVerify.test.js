/**
 * Tests for MFAVerify component.
 *
 * Test cases from workstream-3-security-hardening-mfa.md Section 8.7-8.9:
 * - TC-MFA-04: Login with valid TOTP code
 * - TC-MFA-05: Login with invalid TOTP code
 * - TC-MFA-08: Login with valid backup code
 * - TC-MFA-12: Remember device checkbox
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import MFAVerify from '../../../components/MFA/MFAVerify';

// Mock the auth service
const mockVerifyMFA = jest.fn();
const mockVerifyMFABackupCode = jest.fn();

jest.mock('../../../services/auth', () => ({
  useAuth: () => ({
    verifyMFA: mockVerifyMFA,
    verifyMFABackupCode: mockVerifyMFABackupCode,
  }),
}));

describe('MFAVerify', () => {
  const mockOnSuccess = jest.fn();
  const mfaToken = 'test-mfa-token';

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    test('should render TOTP input form', () => {
      render(<MFAVerify mfaToken={mfaToken} onSuccess={mockOnSuccess} />);
      expect(screen.getByText('Two-Factor Verification')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('000000')).toBeInTheDocument();
    });

    test('should show remember device checkbox', () => {
      render(<MFAVerify mfaToken={mfaToken} onSuccess={mockOnSuccess} />);
      expect(screen.getByText('Remember this device for 30 days')).toBeInTheDocument();
    });

    test('should show backup code option', () => {
      render(<MFAVerify mfaToken={mfaToken} onSuccess={mockOnSuccess} />);
      expect(screen.getByText('Use a backup code instead')).toBeInTheDocument();
    });
  });

  describe('TC-MFA-04: Login with valid TOTP code', () => {
    test('should call onSuccess after valid TOTP verification', async () => {
      mockVerifyMFA.mockResolvedValueOnce({ success: true });

      render(<MFAVerify mfaToken={mfaToken} onSuccess={mockOnSuccess} />);

      const input = screen.getByPlaceholderText('000000');
      fireEvent.change(input, { target: { value: '123456' } });
      fireEvent.click(screen.getByText('Verify'));

      await waitFor(() => {
        expect(mockVerifyMFA).toHaveBeenCalledWith(mfaToken, '123456', false);
        expect(mockOnSuccess).toHaveBeenCalled();
      });
    });

    test('should pass remember device flag when checked', async () => {
      mockVerifyMFA.mockResolvedValueOnce({ success: true });

      render(<MFAVerify mfaToken={mfaToken} onSuccess={mockOnSuccess} />);

      const checkbox = screen.getByLabelText('Remember this device for 30 days');
      fireEvent.click(checkbox);

      const input = screen.getByPlaceholderText('000000');
      fireEvent.change(input, { target: { value: '123456' } });
      fireEvent.click(screen.getByText('Verify'));

      await waitFor(() => {
        expect(mockVerifyMFA).toHaveBeenCalledWith(mfaToken, '123456', true);
      });
    });
  });

  describe('TC-MFA-05: Login with invalid TOTP code', () => {
    test('should show error for invalid code', async () => {
      mockVerifyMFA.mockResolvedValueOnce({
        success: false,
        error: 'Invalid verification code',
      });

      render(<MFAVerify mfaToken={mfaToken} onSuccess={mockOnSuccess} />);

      const input = screen.getByPlaceholderText('000000');
      fireEvent.change(input, { target: { value: '000000' } });
      fireEvent.click(screen.getByText('Verify'));

      await waitFor(() => {
        expect(screen.getByText('Invalid verification code')).toBeInTheDocument();
        expect(mockOnSuccess).not.toHaveBeenCalled();
      });
    });
  });

  describe('Input validation', () => {
    test('should only accept digits in TOTP input', () => {
      render(<MFAVerify mfaToken={mfaToken} onSuccess={mockOnSuccess} />);

      const input = screen.getByPlaceholderText('000000');
      fireEvent.change(input, { target: { value: 'abc123' } });
      expect(input.value).toBe('123');
    });

    test('should limit TOTP input to 6 digits', () => {
      render(<MFAVerify mfaToken={mfaToken} onSuccess={mockOnSuccess} />);

      const input = screen.getByPlaceholderText('000000');
      fireEvent.change(input, { target: { value: '12345678' } });
      expect(input.value).toBe('123456');
    });

    test('should disable verify button when code is less than 6 digits', () => {
      render(<MFAVerify mfaToken={mfaToken} onSuccess={mockOnSuccess} />);

      const input = screen.getByPlaceholderText('000000');
      fireEvent.change(input, { target: { value: '123' } });
      expect(screen.getByText('Verify')).toBeDisabled();
    });
  });

  describe('Backup code flow', () => {
    test('should switch to backup code input on click', () => {
      render(<MFAVerify mfaToken={mfaToken} onSuccess={mockOnSuccess} />);

      fireEvent.click(screen.getByText('Use a backup code instead'));
      // Should show BackupCodeInput component
      expect(screen.queryByText('Two-Factor Verification')).not.toBeInTheDocument();
    });
  });
});
