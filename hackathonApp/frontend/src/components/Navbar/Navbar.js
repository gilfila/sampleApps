import React from 'react';
import { Link } from 'react-router-dom';
import './Navbar.css';

function Navbar({ user, onLogout }) {
  return (
    <nav className="navbar">
      <div>
        <Link to="/dashboard">Hackathon App</Link>
      </div>
      <div className="navbar-links">
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/tickets">Tickets</Link>
        <Link to="/chat">Chat</Link>
        <Link to="/leaderboard">Leaderboard</Link>
        <Link to="/worker-profile">Logan&apos;s Profile</Link>
        <Link to="/settings/security">Settings</Link>
        {user?.role === 'admin' && (
          <>
            <Link to="/admin/mfa">Admin (MFA)</Link>
            <Link to="/admin/users">Users</Link>
          </>
        )}
        {user && (
          <span className="navbar-user">
            {user.name} ({user.role})
          </span>
        )}
        <button className="btn btn-secondary" onClick={onLogout}>
          Logout
        </button>
      </div>
    </nav>
  );
}

export default Navbar;
