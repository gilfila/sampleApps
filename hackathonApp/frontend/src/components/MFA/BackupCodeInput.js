import React, { useState } from 'react';
import { useAuth } from '../../services/auth';

function BackupCodeInput({ mfaToken, onSuccess, onBack }) {
  const { verifyMFABackupCode } = useAuth();
  const [backupCode, setBackupCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const result = await verifyMFABackupCode(mfaToken, backupCode);

    if (result.success) {
      if (result.backupCodesRemaining <= 2) {
        alert(`Warning: You only have ${result.backupCodesRemaining} backup codes remaining. Please generate new ones in your security settings.`);
      }
      onSuccess();
    } else {
      setError(result.error);
    }

    setLoading(false);
  };

  return (
    <div className="auth-card">
      <h2>Enter Backup Code</h2>
      <p style={{ textAlign: 'center', color: '#666', marginBottom: '20px' }}>
        Enter one of your backup codes
      </p>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <input
            type="text"
            value={backupCode}
            onChange={(e) => setBackupCode(e.target.value.toUpperCase())}
            placeholder="ABCD1234"
            autoFocus
            style={{ textAlign: 'center', fontSize: '18px', letterSpacing: '4px' }}
          />
        </div>
        {error && <div className="error">{error}</div>}
        <button
          type="submit"
          className="btn btn-primary"
          disabled={loading || !backupCode.trim()}
          style={{ width: '100%' }}
        >
          {loading ? 'Verifying...' : 'Verify'}
        </button>
      </form>
      <div style={{ textAlign: 'center', marginTop: '16px' }}>
        <button
          className="btn btn-secondary"
          onClick={onBack}
          style={{ fontSize: '14px', padding: '6px 12px' }}
        >
          Back to authenticator code
        </button>
      </div>
    </div>
  );
}

export default BackupCodeInput;
