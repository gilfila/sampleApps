import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../services/auth';
import api from '../../services/api';
import Navbar from '../Navbar/Navbar';

function MFAManagement() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [policy, setPolicy] = useState('optional');
  const [users, setUsers] = useState([]);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [policyLoading, setPolicyLoading] = useState(false);
  const [error, setError] = useState('');
  const [resetMessage, setResetMessage] = useState('');

  useEffect(() => {
    fetchStats();
    fetchUsers();
  }, []);

  useEffect(() => {
    fetchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, search]);

  const fetchStats = async () => {
    try {
      const res = await api.get('/admin/mfa/status');
      setStats(res.data);
      setPolicy(res.data.enforcement);
    } catch (err) {
      setError('Failed to load MFA statistics');
    }
  };

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/mfa/users', {
        params: { search, page, per_page: 20 },
      });
      setUsers(res.data.users || []);
      setTotalPages(res.data.total_pages || 1);
    } catch (err) {
      setError('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const handlePolicySave = async () => {
    setPolicyLoading(true);
    try {
      await api.put('/admin/mfa/enforcement', { policy });
      fetchStats();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to update policy');
    } finally {
      setPolicyLoading(false);
    }
  };

  const handleResetMFA = async (userId, email) => {
    if (!window.confirm(`Reset MFA for ${email}? This will remove their two-factor authentication.`)) {
      return;
    }
    try {
      await api.post(`/admin/mfa/reset/${userId}`);
      setResetMessage(`MFA reset for ${email}`);
      fetchUsers();
      fetchStats();
      setTimeout(() => setResetMessage(''), 3000);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to reset MFA');
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const enrollmentPercent = stats
    ? Math.round((stats.mfa_enabled / stats.total_users) * 100)
    : 0;

  return (
    <div>
      <Navbar user={user} onLogout={handleLogout} />
      <div className="container">
        <h1>MFA Management</h1>

        {error && <div className="error" style={{ marginBottom: '12px' }}>{error}</div>}
        {resetMessage && <div className="success" style={{ marginBottom: '12px' }}>{resetMessage}</div>}

        {/* Policy Section */}
        <div className="card">
          <h3>MFA Enforcement Policy</h3>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', cursor: 'pointer' }}>
              <input
                type="radio"
                name="policy"
                value="optional"
                checked={policy === 'optional'}
                onChange={(e) => setPolicy(e.target.value)}
                style={{ marginRight: '8px', width: 'auto' }}
              />
              Optional
            </label>
            <label style={{ display: 'block', marginBottom: '8px', cursor: 'pointer' }}>
              <input
                type="radio"
                name="policy"
                value="required_for_admins"
                checked={policy === 'required_for_admins'}
                onChange={(e) => setPolicy(e.target.value)}
                style={{ marginRight: '8px', width: 'auto' }}
              />
              Required for Admins and Experts
            </label>
            <label style={{ display: 'block', marginBottom: '8px', cursor: 'pointer' }}>
              <input
                type="radio"
                name="policy"
                value="required_for_all"
                checked={policy === 'required_for_all'}
                onChange={(e) => setPolicy(e.target.value)}
                style={{ marginRight: '8px', width: 'auto' }}
              />
              Required for All Users
            </label>
          </div>
          <button
            className="btn btn-primary"
            onClick={handlePolicySave}
            disabled={policyLoading}
          >
            {policyLoading ? 'Saving...' : 'Save Policy'}
          </button>
        </div>

        {/* Stats Section */}
        {stats && (
          <div className="card">
            <h3>MFA Statistics</h3>
            <p>
              Enrolled: {stats.mfa_enabled}/{stats.total_users} ({enrollmentPercent}%)
            </p>
            <div style={{
              background: '#e9ecef',
              borderRadius: '8px',
              height: '24px',
              marginBottom: '12px',
              overflow: 'hidden',
            }}>
              <div style={{
                background: '#28a745',
                height: '100%',
                width: `${enrollmentPercent}%`,
                borderRadius: '8px',
                transition: 'width 0.3s',
              }} />
            </div>
            <p>Trusted Devices: {stats.trusted_devices}</p>
            {stats.recent_lockouts !== undefined && (
              <p>Failed MFA attempts (24h): {stats.recent_lockouts}</p>
            )}
          </div>
        )}

        {/* Users Section */}
        <div className="card">
          <h3>User MFA Status</h3>
          <div className="form-group" style={{ maxWidth: '300px' }}>
            <input
              type="text"
              placeholder="Search users..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </div>

          {loading ? (
            <p>Loading users...</p>
          ) : (
            <>
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>MFA</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td>{u.name}</td>
                      <td>{u.email}</td>
                      <td>
                        <span style={{
                          color: u.mfa_enabled ? '#28a745' : '#6c757d',
                          fontWeight: 600,
                        }}>
                          {u.mfa_enabled ? 'Yes' : 'No'}
                        </span>
                      </td>
                      <td>
                        {u.mfa_enabled ? (
                          <button
                            className="btn btn-danger"
                            style={{ padding: '4px 8px', fontSize: '13px' }}
                            onClick={() => handleResetMFA(u.id, u.email)}
                          >
                            Reset
                          </button>
                        ) : (
                          '--'
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {totalPages > 1 && (
                <div style={{ display: 'flex', gap: '8px', marginTop: '16px', justifyContent: 'center' }}>
                  <button
                    className="btn btn-secondary"
                    disabled={page <= 1}
                    onClick={() => setPage(page - 1)}
                    style={{ padding: '4px 12px' }}
                  >
                    Previous
                  </button>
                  <span style={{ padding: '6px 12px' }}>
                    Page {page} of {totalPages}
                  </span>
                  <button
                    className="btn btn-secondary"
                    disabled={page >= totalPages}
                    onClick={() => setPage(page + 1)}
                    style={{ padding: '4px 12px' }}
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default MFAManagement;
