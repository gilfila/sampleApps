import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../services/auth';
import api from '../../services/api';
import Navbar from '../Navbar/Navbar';
import MFAEnrollment from '../MFA/MFAEnrollment';
import TrustedDevices from './TrustedDevices';
import CursorCLISetup from './CursorCLISetup';

function SecuritySettings() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mfaEnabled, setMfaEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showEnrollment, setShowEnrollment] = useState(false);
  const [disablePassword, setDisablePassword] = useState('');
  const [disableTotpCode, setDisableTotpCode] = useState('');
  const [disableError, setDisableError] = useState('');
  const [disableLoading, setDisableLoading] = useState(false);
  const [regeneratePassword, setRegeneratePassword] = useState('');
  const [regenerateError, setRegenerateError] = useState('');
  const [regenerateLoading, setRegenerateLoading] = useState(false);
  const [newBackupCodes, setNewBackupCodes] = useState(null);

  useEffect(() => {
    checkMFAStatus();
  }, []);

  const checkMFAStatus = async () => {
    try {
      const res = await api.get('/auth/mfa/status');
      setMfaEnabled(res.data.is_enabled);
    } catch (err) {
      console.error('Failed to check MFA status:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleEnrollmentComplete = () => {
    setShowEnrollment(false);
    setMfaEnabled(true);
  };

  const handleDisableMFA = async (e) => {
    e.preventDefault();
    setDisableError('');
    setDisableLoading(true);
    try {
      await api.delete('/auth/mfa/disable', {
        data: {
          password: disablePassword,
          totp_code: disableTotpCode,
        },
      });
      setMfaEnabled(false);
      setDisablePassword('');
      setDisableTotpCode('');
    } catch (err) {
      setDisableError(err.response?.data?.error || 'Failed to disable MFA');
    } finally {
      setDisableLoading(false);
    }
  };

  const handleRegenerateBackupCodes = async (e) => {
    e.preventDefault();
    setRegenerateError('');
    setRegenerateLoading(true);
    try {
      const res = await api.post('/auth/mfa/backup-codes', {
        password: regeneratePassword,
      });
      setNewBackupCodes(res.data.backup_codes);
      setRegeneratePassword('');
    } catch (err) {
      setRegenerateError(err.response?.data?.error || 'Failed to regenerate codes');
    } finally {
      setRegenerateLoading(false);
    }
  };

  if (loading) {
    return (
      <div>
        <Navbar user={user} onLogout={handleLogout} />
        <div className="container"><p>Loading...</p></div>
      </div>
    );
  }

  return (
    <div>
      <Navbar user={user} onLogout={handleLogout} />
      <div className="container">
        <h1>Account Security Settings</h1>

        <div className="card">
          <h3>Two-Factor Authentication</h3>
          <p style={{ marginBottom: '16px' }}>
            Status: <strong style={{ color: mfaEnabled ? '#28a745' : '#dc3545' }}>
              {mfaEnabled ? 'Enabled' : 'Not Enabled'}
            </strong>
          </p>

          {!mfaEnabled && !showEnrollment && (
            <div>
              <p style={{ color: '#666', marginBottom: '16px' }}>
                Add an extra layer of security to your account by requiring a verification code
                from your authenticator app.
              </p>
              <button
                className="btn btn-primary"
                onClick={() => setShowEnrollment(true)}
              >
                Enable Two-Factor Authentication
              </button>
            </div>
          )}

          {showEnrollment && (
            <MFAEnrollment
              onComplete={handleEnrollmentComplete}
              onCancel={() => setShowEnrollment(false)}
            />
          )}

          {mfaEnabled && (
            <div>
              {/* Regenerate Backup Codes */}
              <div style={{ marginBottom: '24px', paddingBottom: '24px', borderBottom: '1px solid #eee' }}>
                <h4>Backup Codes</h4>
                {newBackupCodes ? (
                  <div>
                    <p style={{ color: '#666' }}>New backup codes generated. Save these securely:</p>
                    <div style={{
                      background: '#f8f9fa',
                      border: '1px solid #dee2e6',
                      borderRadius: '8px',
                      padding: '16px',
                      marginBottom: '12px',
                      fontFamily: 'monospace',
                    }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                        {newBackupCodes.map((code, i) => (
                          <div key={i} style={{ textAlign: 'center' }}>{code}</div>
                        ))}
                      </div>
                    </div>
                    <button className="btn btn-secondary" onClick={() => setNewBackupCodes(null)}>
                      Done
                    </button>
                  </div>
                ) : (
                  <form onSubmit={handleRegenerateBackupCodes}>
                    <p style={{ color: '#666', marginBottom: '12px' }}>
                      Generate new backup codes. This will invalidate your existing codes.
                    </p>
                    <div className="form-group" style={{ maxWidth: '300px' }}>
                      <label>Current Password</label>
                      <input
                        type="password"
                        value={regeneratePassword}
                        onChange={(e) => setRegeneratePassword(e.target.value)}
                        required
                      />
                    </div>
                    {regenerateError && <div className="error" style={{ marginBottom: '8px' }}>{regenerateError}</div>}
                    <button type="submit" className="btn btn-primary" disabled={regenerateLoading}>
                      {regenerateLoading ? 'Generating...' : 'Regenerate Backup Codes'}
                    </button>
                  </form>
                )}
              </div>

              {/* Disable MFA */}
              <div style={{ marginBottom: '24px', paddingBottom: '24px', borderBottom: '1px solid #eee' }}>
                <h4>Disable Two-Factor Authentication</h4>
                <form onSubmit={handleDisableMFA}>
                  <div className="form-group" style={{ maxWidth: '300px' }}>
                    <label>Current Password</label>
                    <input
                      type="password"
                      value={disablePassword}
                      onChange={(e) => setDisablePassword(e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-group" style={{ maxWidth: '300px' }}>
                    <label>TOTP Code</label>
                    <input
                      type="text"
                      value={disableTotpCode}
                      onChange={(e) => {
                        const val = e.target.value.replace(/\D/g, '').slice(0, 6);
                        setDisableTotpCode(val);
                      }}
                      placeholder="000000"
                      maxLength={6}
                      required
                    />
                  </div>
                  {disableError && <div className="error" style={{ marginBottom: '8px' }}>{disableError}</div>}
                  <button type="submit" className="btn btn-danger" disabled={disableLoading}>
                    {disableLoading ? 'Disabling...' : 'Disable MFA'}
                  </button>
                </form>
              </div>

              {/* Trusted Devices */}
              <TrustedDevices />
            </div>
          )}
        </div>

        {/* Cursor CLI / Developer — connect Cursor to Workday MCP */}
        <CursorCLISetup />
      </div>
    </div>
  );
}

export default SecuritySettings;
