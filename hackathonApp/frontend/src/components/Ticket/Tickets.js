import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../services/auth';
import api from '../../services/api';
import Navbar from '../Navbar/Navbar';
import './Ticket.css';

function Tickets() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState({
    description: '',
    location_table: '',
    priority: 'normal',
  });

  useEffect(() => {
    fetchTickets();
  }, []);

  const fetchTickets = async () => {
    try {
      const response = await api.get('/tickets');
      setTickets(response.data.tickets);
    } catch (error) {
      console.error('Error fetching tickets:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTicket = async (e) => {
    e.preventDefault();
    try {
      await api.post('/tickets', formData);
      setShowCreateForm(false);
      setFormData({ description: '', location_table: '', priority: 'normal' });
      fetchTickets();
    } catch (error) {
      console.error('Error creating ticket:', error);
      alert('Failed to create ticket');
    }
  };

  const handleAssignTicket = async (ticketId) => {
    try {
      await api.post(`/tickets/${ticketId}/assign`);
      fetchTickets();
    } catch (error) {
      console.error('Error assigning ticket:', error);
      alert('Failed to assign ticket');
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div>
      <Navbar user={user} onLogout={handleLogout} />
      <div className="container">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h1>Tickets</h1>
          <button className="btn btn-primary" onClick={() => setShowCreateForm(!showCreateForm)}>
            {showCreateForm ? 'Cancel' : 'Create Ticket'}
          </button>
        </div>

        {showCreateForm && (
          <div className="card">
            <h2>Create New Ticket</h2>
            <form onSubmit={handleCreateTicket}>
              <div className="form-group">
                <label>Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Location/Table</label>
                <input
                  type="text"
                  value={formData.location_table}
                  onChange={(e) => setFormData({ ...formData, location_table: e.target.value })}
                  placeholder={user?.table || 'Enter table number'}
                />
              </div>
              <div className="form-group">
                <label>Priority</label>
                <select
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                >
                  <option value="normal">Normal</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
              </div>
              <button type="submit" className="btn btn-primary">Create Ticket</button>
            </form>
          </div>
        )}

        <div className="card">
          {loading ? (
            <p>Loading...</p>
          ) : tickets.length === 0 ? (
            <p>No tickets found</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Ticket #</th>
                  <th>Description</th>
                  <th>Status</th>
                  <th>Priority</th>
                  <th>Reporter</th>
                  <th>Assignee</th>
                  <th>Location</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {tickets.map((ticket) => (
                  <tr key={ticket.id}>
                    <td>{ticket.ticket_number}</td>
                    <td>{ticket.description.substring(0, 50)}...</td>
                    <td>
                      <span className={`badge badge-${ticket.status.replace('_', '-')}`}>
                        {ticket.status}
                      </span>
                    </td>
                    <td>{ticket.priority}</td>
                    <td>{ticket.reporter.name}</td>
                    <td>{ticket.assignee?.name || 'Unassigned'}</td>
                    <td>{ticket.location_table || 'N/A'}</td>
                    <td>
                      <button
                        className="btn btn-primary"
                        onClick={() => navigate(`/tickets/${ticket.id}`)}
                        style={{ marginRight: '5px' }}
                      >
                        View
                      </button>
                      {user?.role === 'expert' || user?.role === 'admin' ? (
                        !ticket.assignee && (
                          <button
                            className="btn btn-success"
                            onClick={() => handleAssignTicket(ticket.id)}
                          >
                            Assign to Me
                          </button>
                        )
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

export default Tickets;
