import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../services/auth';
import api from '../../services/api';
import Navbar from '../Navbar/Navbar';
import './Leaderboard.css';

function Leaderboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLeaderboard();
  }, []);

  const fetchLeaderboard = async () => {
    try {
      const response = await api.get('/tickets/leaderboard');
      setLeaderboard(response.data.leaderboard);
    } catch (error) {
      console.error('Error fetching leaderboard:', error);
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
        <h1>Expert Leaderboard</h1>
        <div className="card">
          {loading ? (
            <p>Loading...</p>
          ) : leaderboard.length === 0 ? (
            <p>No closed tickets yet</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Expert</th>
                  <th>Email</th>
                  <th>Closed Tickets</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((entry, index) => (
                  <tr key={entry.worker_id}>
                    <td>#{index + 1}</td>
                    <td>{entry.name}</td>
                    <td>{entry.email}</td>
                    <td>
                      <strong>{entry.closed_count}</strong>
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

export default Leaderboard;
