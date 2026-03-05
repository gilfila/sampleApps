import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../services/auth';
import api from '../../services/api';
import Navbar from '../Navbar/Navbar';
import './Ticket.css';

function TicketDetail() {
  const { id } = useParams();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState('');

  useEffect(() => {
    fetchTicket();
  }, [id]);

  const fetchTicket = async () => {
    try {
      const response = await api.get(`/tickets/${id}`);
      setTicket(response.data);
      setStatus(response.data.status);
    } catch (error) {
      console.error('Error fetching ticket:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateStatus = async () => {
    try {
      await api.put(`/tickets/${id}`, { status });
      fetchTicket();
    } catch (error) {
      console.error('Error updating ticket:', error);
      alert('Failed to update ticket');
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  if (loading) {
    return (
      <div>
        <Navbar user={user} onLogout={handleLogout} />
        <div className="container">
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (!ticket) {
    return (
      <div>
        <Navbar user={user} onLogout={handleLogout} />
        <div className="container">
          <p>Ticket not found</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <Navbar user={user} onLogout={handleLogout} />
      <div className="container">
        <button className="btn btn-secondary" onClick={() => navigate('/tickets')} style={{ marginBottom: '20px' }}>
          Back to Tickets
        </button>
        <div className="card">
          <h1>Ticket #{ticket.ticket_number}</h1>
          <div className="ticket-details">
            <p><strong>Status:</strong> 
              <span className={`badge badge-${ticket.status.replace('_', '-')}`} style={{ marginLeft: '10px' }}>
                {ticket.status}
              </span>
            </p>
            <p><strong>Priority:</strong> {ticket.priority}</p>
            <p><strong>Reporter:</strong> {ticket.reporter.name} ({ticket.reporter.email})</p>
            <p><strong>Assignee:</strong> {ticket.assignee?.name || 'Unassigned'}</p>
            <p><strong>Location/Table:</strong> {ticket.location_table || 'N/A'}</p>
            <p><strong>Opened:</strong> {new Date(ticket.ticket_opened).toLocaleString()}</p>
            {ticket.ticket_closed && (
              <p><strong>Closed:</strong> {new Date(ticket.ticket_closed).toLocaleString()}</p>
            )}
            {ticket.time_to_closed && (
              <p><strong>Time to Close:</strong> {ticket.time_to_closed}</p>
            )}
          </div>
          <div className="ticket-description">
            <h3>Description</h3>
            <p>{ticket.description}</p>
          </div>
          {(user?.role === 'expert' || user?.role === 'admin') && (
            <div className="ticket-actions">
              <h3>Update Status</h3>
              <select value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="closed">Closed</option>
                <option value="duplicate">Duplicate</option>
              </select>
              <button className="btn btn-primary" onClick={handleUpdateStatus} style={{ marginLeft: '10px' }}>
                Update
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default TicketDetail;
