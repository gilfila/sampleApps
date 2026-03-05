import React, { useState, useEffect } from 'react';
import api from '../../services/api';

function TrustedDevices() {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchDevices();
  }, []);

  const fetchDevices = async () => {
    try {
      const res = await api.get('/auth/mfa/trusted-devices');
      setDevices(res.data.devices || []);
    } catch (err) {
      setError('Failed to load trusted devices');
    } finally {
      setLoading(false);
    }
  };

  const revokeDevice = async (deviceId) => {
    try {
      await api.delete(`/auth/mfa/trusted-devices/${deviceId}`);
      setDevices(devices.filter((d) => d.id !== deviceId));
    } catch (err) {
      setError('Failed to revoke device');
    }
  };

  if (loading) return <p>Loading trusted devices...</p>;

  return (
    <div>
      <h4>Trusted Devices</h4>
      {error && <div className="error" style={{ marginBottom: '12px' }}>{error}</div>}
      {devices.length === 0 ? (
        <p style={{ color: '#666' }}>No trusted devices</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Device</th>
              <th>IP Address</th>
              <th>Last Used</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {devices.map((device) => (
              <tr key={device.id}>
                <td>{device.user_agent || 'Unknown device'}</td>
                <td>{device.ip_address || 'Unknown'}</td>
                <td>{new Date(device.last_used_at).toLocaleDateString()}</td>
                <td>
                  <button
                    className="btn btn-danger"
                    style={{ padding: '4px 8px', fontSize: '13px' }}
                    onClick={() => revokeDevice(device.id)}
                  >
                    Revoke
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default TrustedDevices;
