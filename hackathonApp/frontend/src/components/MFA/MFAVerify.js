import React, { useState } from 'react';
import { useAuth } from '../../services/auth';
import BackupCodeInput from './BackupCodeInput';

function MFAVerify({ mfaToken, onSuccess }) {
  const { verifyMFA } = useAuth();
  const [totpCode, setTotpCode] = useState('');
  const [rememberDevice, setRememberDevice] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showBackupCode, setShowBackupCode] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const result = await verifyMFA(mfaToken, totpCode, rememberDevice);

    if (result.success) {
      onSuccess();
    } else {
      setError(result.error);
    }

    setLoading(false);
  };

  if (showBackupCode) {
    return (
      <BackupCodeInput
        mfaToken={mfaToken}
        onSuccess={onSuccess}
        onBack={() => setShowBackupCode(false)}
      />
    );
  }

  return (
    <div className="auth-card">
      <h2>Two-Factor Verification</h2>
      <p style={{ textAlign: 'center', color: '#666', marginBottom: '20px' }}>
        Enter the 6-digit code from your authenticator app
      </p>
      <form onSubmit={handleSubmit}>
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
            autoFocus
            style={{ textAlign: 'center', fontSize: '24px', letterSpacing: '8px' }}
          />
        </div>
        <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <input
            type="checkbox"
            id="rememberDevice"
            checked={rememberDevice}
            onChange={(e) => setRememberDevice(e.target.checked)}
            style={{ width: 'auto' }}
          />
          <label htmlFor="rememberDevice" style={{ fontWeight: 'normal', marginBottom: 0 }}>
            Remember this device for 30 days
          </label>
        </div>
        {error && <div className="error">{error}</div>}
        <button type="submit" className="btn btn-primary" disabled={loading || totpCode.length !== 6} style={{ width: '100%' }}>
          {loading ? 'Verifying...' : 'Verify'}
        </button>
      </form>
      <div style={{ textAlign: 'center', marginTop: '20px', borderTop: '1px solid #eee', paddingTop: '16px' }}>
        <p style={{ color: '#666', fontSize: '14px' }}>Lost your authenticator?</p>
        <button
          className="btn btn-secondary"
          onClick={() => setShowBackupCode(true)}
          style={{ fontSize: '14px', padding: '6px 12px' }}
        >
          Use a backup code instead
        </button>
      </div>
    </div>
  );
}

export default MFAVerify;
