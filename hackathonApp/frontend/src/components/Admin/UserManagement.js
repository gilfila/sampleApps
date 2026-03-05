import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../services/auth';
import api from '../../services/api';
import Navbar from '../Navbar/Navbar';
import './UserManagement.css';

const ROLES = ['hacker', 'expert', 'admin'];

function UserManagement() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [workers, setWorkers] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, per_page: 50, total: 0, pages: 1 });
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  // Add-user form
  const [newEmail, setNewEmail] = useState('');
  const [newName, setNewName] = useState('');
  const [newRole, setNewRole] = useState('hacker');
  const [adding, setAdding] = useState(false);

  // Inline edit state per row: { workerId: { name, role, is_active } }
  const [edits, setEdits] = useState({});
  const [savingId, setSavingId] = useState(null);

  useEffect(() => {
    if (user?.role !== 'admin') {
      navigate('/dashboard');
      return;
    }
    fetchWorkers();
  }, [user?.role, navigate, pagination.page, search]);

  const fetchWorkers = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get('/workers', {
        params: {
          page: pagination.page,
          per_page: pagination.per_page,
          ...(search.trim() && { search: search.trim() }),
        },
      });
      setWorkers(res.data.workers || []);
      setPagination(prev => ({
        ...prev,
        total: res.data.pagination?.total ?? 0,
        pages: res.data.pagination?.pages ?? 1,
      }));
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load users');
      setWorkers([]);
    } finally {
      setLoading(false);
    }
  };

  const getEdit = (w) => edits[w.id] ?? { name: w.name, role: w.role, is_active: w.is_active };

  const setEdit = (workerId, field, value) => {
    setEdits(prev => {
      const current = prev[workerId] ?? {};
      return { ...prev, [workerId]: { ...current, [field]: value } };
    });
  };

  const initEdit = (w) => {
    setEdits(prev => ({ ...prev, [w.id]: { name: w.name, role: w.role, is_active: w.is_active } }));
  };

  const handleSave = async (w) => {
    const patch = getEdit(w);
    if (patch.name === w.name && patch.role === w.role && patch.is_active === w.is_active) {
      setMessage('No changes to save');
      setTimeout(() => setMessage(''), 2000);
      return;
    }
    setSavingId(w.id);
    setError('');
    try {
      await api.patch(`/workers/${w.id}`, {
        name: patch.name,
        role: patch.role,
        is_active: patch.is_active,
      });
      setMessage(`Saved ${w.email}`);
      setTimeout(() => setMessage(''), 3000);
      setEdits(prev => {
        const next = { ...prev };
        delete next[w.id];
        return next;
      });
      fetchWorkers();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to update user');
    } finally {
      setSavingId(null);
    }
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    const email = (newEmail || '').trim().toLowerCase();
    const name = (newName || '').trim();
    if (!email) {
      setError('Email is required');
      return;
    }
    if (!name) {
      setError('Name is required');
      return;
    }
    setAdding(true);
    setError('');
    try {
      await api.post('/workers', { email, name, role: newRole });
      setMessage(`Added ${email}. They can now register at /register.`);
      setTimeout(() => setMessage(''), 4000);
      setNewEmail('');
      setNewName('');
      setNewRole('hacker');
      fetchWorkers();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to add user');
    } finally {
      setAdding(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  if (user?.role !== 'admin') {
    return null;
  }

  return (
    <div>
      <Navbar user={user} onLogout={handleLogout} />
      <div className="container">
        <h1>User Management</h1>
        <p className="user-mgmt-subtitle">
          Add users so they can register, or update name, role, and active status.
        </p>

        {error && <div className="error user-mgmt-msg">{error}</div>}
        {message && <div className="success user-mgmt-msg">{message}</div>}

        <div className="card user-mgmt-card">
          <h3>Add user</h3>
          <form onSubmit={handleAdd} className="user-mgmt-add-form">
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="new-email">Email</label>
                <input
                  id="new-email"
                  type="email"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="user@example.com"
                  disabled={adding}
                />
              </div>
              <div className="form-group">
                <label htmlFor="new-name">Name</label>
                <input
                  id="new-name"
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Display name"
                  disabled={adding}
                />
              </div>
              <div className="form-group">
                <label htmlFor="new-role">Role</label>
                <select
                  id="new-role"
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  disabled={adding}
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </div>
              <div className="form-group form-group-actions">
                <label>&nbsp;</label>
                <button type="submit" className="btn btn-primary" disabled={adding}>
                  {adding ? 'Adding...' : 'Add user'}
                </button>
              </div>
            </div>
          </form>
        </div>

        <div className="card user-mgmt-card">
          <h3>Users</h3>
          <div className="form-group user-mgmt-search">
            <input
              type="text"
              placeholder="Search by name or email..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPagination(p => ({ ...p, page: 1 })); }}
            />
          </div>

          {loading ? (
            <p>Loading users...</p>
          ) : (
            <>
              <div className="table-wrapper">
                <table className="table user-mgmt-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Email</th>
                      <th>Name</th>
                      <th>Role</th>
                      <th>Active</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {workers.length === 0 ? (
                      <tr>
                        <td colSpan={6}>No users found. Add one above or run Workday sync.</td>
                      </tr>
                    ) : (
                      workers.map((w) => {
                        const e = getEdit(w);
                        const hasEdit = edits[w.id] != null;
                        return (
                          <tr key={w.id}>
                            <td>{w.id}</td>
                            <td className="email-cell">{w.email}</td>
                            <td>
                              {hasEdit ? (
                                <input
                                  type="text"
                                  className="inline-edit"
                                  value={e.name}
                                  onChange={(ev) => setEdit(w.id, 'name', ev.target.value)}
                                />
                              ) : (
                                <span
                                  className="editable"
                                  onClick={() => initEdit(w)}
                                  onKeyDown={(ev) => ev.key === 'Enter' && initEdit(w)}
                                  role="button"
                                  tabIndex={0}
                                >
                                  {w.name}
                                </span>
                              )}
                            </td>
                            <td>
                              {hasEdit ? (
                                <select
                                  className="inline-edit"
                                  value={e.role}
                                  onChange={(ev) => setEdit(w.id, 'role', ev.target.value)}
                                >
                                  {ROLES.map((r) => (
                                    <option key={r} value={r}>{r}</option>
                                  ))}
                                </select>
                              ) : (
                                <span
                                  className="editable"
                                  onClick={() => initEdit(w)}
                                  onKeyDown={(ev) => ev.key === 'Enter' && initEdit(w)}
                                  role="button"
                                  tabIndex={0}
                                >
                                  {w.role}
                                </span>
                              )}
                            </td>
                            <td>
                              {hasEdit ? (
                                <select
                                  className="inline-edit"
                                  value={e.is_active ? 'true' : 'false'}
                                  onChange={(ev) => setEdit(w.id, 'is_active', ev.target.value === 'true')}
                                >
                                  <option value="true">Yes</option>
                                  <option value="false">No</option>
                                </select>
                              ) : (
                                <span
                                  className="editable"
                                  onClick={() => initEdit(w)}
                                  onKeyDown={(ev) => ev.key === 'Enter' && initEdit(w)}
                                  role="button"
                                  tabIndex={0}
                                >
                                  {w.is_active ? 'Yes' : 'No'}
                                </span>
                              )}
                            </td>
                            <td>
                              {hasEdit ? (
                                <>
                                  <button
                                    type="button"
                                    className="btn btn-primary btn-sm"
                                    onClick={() => handleSave(w)}
                                    disabled={savingId === w.id}
                                  >
                                    {savingId === w.id ? 'Saving...' : 'Save'}
                                  </button>
                                  <button
                                    type="button"
                                    className="btn btn-secondary btn-sm"
                                    onClick={() => setEdits(prev => { const n = { ...prev }; delete n[w.id]; return n; })}
                                    disabled={savingId === w.id}
                                  >
                                    Cancel
                                  </button>
                                </>
                              ) : (
                                <button
                                  type="button"
                                  className="btn btn-secondary btn-sm"
                                  onClick={() => initEdit(w)}
                                >
                                  Edit
                                </button>
                              )}
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>

              {pagination.pages > 1 && (
                <div className="pagination">
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={pagination.page <= 1}
                    onClick={() => setPagination(p => ({ ...p, page: p.page - 1 }))}
                  >
                    Previous
                  </button>
                  <span className="pagination-info">
                    Page {pagination.page} of {pagination.pages} ({pagination.total} total)
                  </span>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={pagination.page >= pagination.pages}
                    onClick={() => setPagination(p => ({ ...p, page: p.page + 1 }))}
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

export default UserManagement;
