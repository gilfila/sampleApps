/**
 * Tests for MFAEnrollment component.
 *
 * Test cases from workstream-3-security-hardening-mfa.md Section 8.6:
 * - TC-MFA-01: Successful MFA enrollment flow
 * - TC-MFA-02: Enrollment verification with invalid code
 * - TC-MFA-03: Cannot enroll when already enrolled
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import MFAEnrollment from '../../../components/MFA/MFAEnrollment';

// Mock the API service
jest.mock('../../../services/api', () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
    get: jest.fn(),
  },
}));

import api from '../../../services/api';

describe('MFAEnrollment', () => {
  const mockOnComplete = jest.fn();
  const mockOnCancel = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Initial render', () => {
    test('should show enable button on initial render', () => {
      render(
        <MFAEnrollment onComplete={mockOnComplete} onCancel={mockOnCancel} />
      );
      expect(screen.getByText('Enable Two-Factor Authentication')).toBeInTheDocument();
    });

    test('should show cancel button when onCancel is provided', () => {
      render(
        <MFAEnrollment onComplete={mockOnComplete} onCancel={mockOnCancel} />
      );
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });
  });

  describe('TC-MFA-01: Enrollment initiation', () => {
    test('should show QR code after clicking enable', async () => {
      api.post.mockResolvedValueOnce({
        data: {
          qr_code: 'data:image/png;base64,fakeQrCode',
          manual_key: 'JBSWY3DPEHPK3PXP',
        },
      });

      render(
        <MFAEnrollment onComplete={mockOnComplete} onCancel={mockOnCancel} />
      );

      fireEvent.click(screen.getByText('Enable Two-Factor Authentication'));

      await waitFor(() => {
        expect(api.post).toHaveBeenCalledWith('/auth/mfa/enroll');
      });

      await waitFor(() => {
        expect(screen.getByText('Step 1: Scan QR Code')).toBeInTheDocument();
        expect(screen.getByText('JBSWY3DPEHPK3PXP')).toBeInTheDocument();
      });
    });

    test('should show error on enrollment failure', async () => {
      api.post.mockRejectedValueOnce({
        response: { data: { error: 'MFA is already enabled' } },
      });

      render(
        <MFAEnrollment onComplete={mockOnComplete} onCancel={mockOnCancel} />
      );

      fireEvent.click(screen.getByText('Enable Two-Factor Authentication'));

      await waitFor(() => {
        expect(screen.getByText('MFA is already enabled')).toBeInTheDocument();
      });
    });
  });

  describe('TC-MFA-02: Verification with invalid code', () => {
    test('should show error for invalid verification code', async () => {
      // Setup: initiate enrollment
      api.post.mockResolvedValueOnce({
        data: {
          qr_code: 'data:image/png;base64,fakeQrCode',
          manual_key: 'JBSWY3DPEHPK3PXP',
        },
      });

      render(
        <MFAEnrollment onComplete={mockOnComplete} onCancel={mockOnCancel} />
      );

      fireEvent.click(screen.getByText('Enable Two-Factor Authentication'));

      await waitFor(() => {
        expect(screen.getByText('Step 2: Verify Code')).toBeInTheDocument();
      });

      // Mock verification failure
      api.post.mockRejectedValueOnce({
        response: { data: { error: 'Invalid verification code' } },
      });

      const input = screen.getByPlaceholderText('000000');
      fireEvent.change(input, { target: { value: '000000' } });
      fireEvent.click(screen.getByText('Verify and Enable'));

      await waitFor(() => {
        expect(screen.getByText('Invalid verification code')).toBeInTheDocument();
      });
    });
  });
});
