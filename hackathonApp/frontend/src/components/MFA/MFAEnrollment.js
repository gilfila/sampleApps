import React, { useState } from 'react';
import api from '../../services/api';
import BackupCodes from './BackupCodes';

function MFAEnrollment({ onComplete, onCancel }) {
  const [step, setStep] = useState('setup'); // 'setup' | 'backup_codes'
  const [qrCode, setQrCode] = useState('');
  const [manualKey, setManualKey] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [backupCodes, setBackupCodes] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [enrolling, setEnrolling] = useState(false);

  const startEnrollment = async () => {
    setEnrolling(true);
    setError('');
    try {
      const res = await api.post('/auth/mfa/enroll');
      setQrCode(res.data.qr_code);
      setManualKey(res.data.manual_key);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to start enrollment');
    } finally {
      setEnrolling(false);
    }
  };

  const verifyCode = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await api.post('/auth/mfa/verify-enrollment', {
        totp_code: totpCode,
      });
      setBackupCodes(res.data.backup_codes);
      setStep('backup_codes');
    } catch (err) {
      setError(err.response?.data?.error || 'Invalid verification code');
    } finally {
      setLoading(false);
    }
  };

  const copyManualKey = () => {
    navigator.clipboard.writeText(manualKey);
  };

  // Initial state -- show enable button
  if (!qrCode && step === 'setup') {
    return (
      <div>
        <h3>Set Up Two-Factor Authentication</h3>
        <p style={{ color: '#666', marginBottom: '20px' }}>
          Add an extra layer of security to your account by requiring a verification code
          from your authenticator app.
        </p>
        {error && <div className="error" style={{ marginBottom: '12px' }}>{error}</div>}
        <button
          className="btn btn-primary"
          onClick={startEnrollment}
          disabled={enrolling}
        >
          {enrolling ? 'Setting up...' : 'Enable Two-Factor Authentication'}
        </button>
        {onCancel && (
          <button className="btn btn-secondary" onClick={onCancel} style={{ marginLeft: '8px' }}>
            Cancel
          </button>
        )}
      </div>
    );
  }

  // Backup codes step
  if (step === 'backup_codes') {
    return (
      <BackupCodes codes={backupCodes} onDone={onComplete} />
    );
  }

  // QR code + verify step
  return (
    <div>
      <h3>Set Up Two-Factor Authentication</h3>

      <div style={{ marginBottom: '24px' }}>
        <h4>Step 1: Scan QR Code</h4>
        <p style={{ color: '#666' }}>
          Open your authenticator app (Google Authenticator, Authy, etc.) and scan this QR code:
        </p>
        {qrCode && (
          <div style={{ textAlign: 'center', margin: '16px 0' }}>
            <img
              src={qrCode}
              alt="MFA QR Code"
              style={{ maxWidth: '200px', border: '4px solid #fff', borderRadius: '8px' }}
            />
          </div>
        )}
        <p style={{ color: '#666', fontSize: '14px' }}>
          Can't scan? Enter this key manually:
        </p>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <code style={{
            background: '#f4f4f4',
            padding: '8px 12px',
            borderRadius: '4px',
            fontFamily: 'monospace',
            fontSize: '14px',
            letterSpacing: '2px',
          }}>
            {manualKey}
          </code>
          <button className="btn btn-secondary" onClick={copyManualKey} style={{ padding: '6px 12px', fontSize: '13px' }}>
            Copy
          </button>
        </div>
      </div>

      <div>
        <h4>Step 2: Verify Code</h4>
        <p style={{ color: '#666' }}>
          Enter the 6-digit code from your authenticator app:
        </p>
        <form onSubmit={verifyCode}>
          <div className="form-group">
            <input
              type="text"
              value={totpCode}
              onChange={(e) => {
                const val = e.target.value.replace(/\D/g, '').slice(0, 6);
                setTotpCode(val);
              }}
              placeholder="000000"
              maxLength={6}
              style={{ textAlign: 'center', fontSize: '24px', letterSpacing: '8px', maxWidth: '200px' }}
            />
          </div>
          {error && <div className="error" style={{ marginBottom: '12px' }}>{error}</div>}
          <div style={{ display: 'flex', gap: '8px' }}>
            {onCancel && (
              <button type="button" className="btn btn-secondary" onClick={onCancel}>
                Cancel
              </button>
            )}
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || totpCode.length !== 6}
            >
              {loading ? 'Verifying...' : 'Verify and Enable'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default MFAEnrollment;
