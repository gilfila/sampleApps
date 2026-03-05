import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../services/auth';
import api from '../../services/api';
import Navbar from '../Navbar/Navbar';
import './Dashboard.css';

function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [activeTickets, setActiveTickets] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      const response = await api.get('/tickets/dashboard');
      setActiveTickets(response.data.active_tickets);
    } catch (error) {
      console.error('Error fetching dashboard:', error);
    } finally {
      setLoading(false);
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
        <h1>Dashboard</h1>
        <div className="dashboard-stats">
          <div className="stat-card">
            <h3>Active Tickets</h3>
            <p className="stat-number">{activeTickets.length}</p>
          </div>
        </div>
        <div className="card">
          <h2>Active Tickets</h2>
          {loading ? (
            <p>Loading...</p>
          ) : activeTickets.length === 0 ? (
            <p>No active tickets</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Ticket #</th>
                  <th>Description</th>
                  <th>Status</th>
                  <th>Reporter</th>
                  <th>Assignee</th>
                  <th>Location</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {activeTickets.map((ticket) => (
                  <tr key={ticket.id}>
                    <td>{ticket.ticket_number}</td>
                    <td>{ticket.description.substring(0, 50)}...</td>
                    <td>
                      <span className={`badge badge-${ticket.status.replace('_', '-')}`}>
                        {ticket.status}
                      </span>
                    </td>
                    <td>{ticket.reporter.name}</td>
                    <td>{ticket.assignee?.name || 'Unassigned'}</td>
                    <td>{ticket.location_table || 'N/A'}</td>
                    <td>
                      <button
                        className="btn btn-primary"
                        onClick={() => navigate(`/tickets/${ticket.id}`)}
                      >
                        View
                      </button>
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

export default Dashboard;
