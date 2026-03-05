import React, { useState } from 'react';

function BackupCodes({ codes, onDone }) {
  const [saved, setSaved] = useState(false);

  const downloadCodes = () => {
    const text = [
      'Hackathon App - Backup Recovery Codes',
      '======================================',
      '',
      'Each code can only be used once.',
      'Store these codes in a safe place.',
      '',
      ...codes.map((code, i) => `${i + 1}. ${code}`),
      '',
      `Generated: ${new Date().toISOString()}`,
    ].join('\n');

    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'hackathon-app-backup-codes.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const copyCodes = () => {
    navigator.clipboard.writeText(codes.join('\n'));
  };

  return (
    <div>
      <h3>Save Your Backup Codes</h3>
      <div style={{
        background: '#fff3cd',
        border: '1px solid #ffc107',
        borderRadius: '8px',
        padding: '16px',
        marginBottom: '20px',
      }}>
        <strong>IMPORTANT:</strong> Save these backup codes in a safe place.
        If you lose access to your authenticator app, you can use these codes to sign in.
        Each code can only be used once.
      </div>

      <div style={{
        background: '#f8f9fa',
        border: '1px solid #dee2e6',
        borderRadius: '8px',
        padding: '20px',
        marginBottom: '20px',
        fontFamily: 'monospace',
        fontSize: '16px',
      }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '12px',
        }}>
          {codes.map((code, index) => (
            <div key={index} style={{ textAlign: 'center', letterSpacing: '2px' }}>
              {code}
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
        <button className="btn btn-primary" onClick={downloadCodes}>
          Download as Text
        </button>
        <button className="btn btn-secondary" onClick={copyCodes}>
          Copy to Clipboard
        </button>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
        <input
          type="checkbox"
          id="savedCodes"
          checked={saved}
          onChange={(e) => setSaved(e.target.checked)}
          style={{ width: 'auto' }}
        />
        <label htmlFor="savedCodes" style={{ fontWeight: 'normal', marginBottom: 0 }}>
          I have saved my backup codes
        </label>
      </div>

      <button
        className="btn btn-success"
        onClick={onDone}
        disabled={!saved}
        style={{ width: '100%' }}
      >
        Done
      </button>
    </div>
  );
}

export default BackupCodes;
