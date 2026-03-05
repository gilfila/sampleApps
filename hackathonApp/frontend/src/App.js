import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './services/auth';
import Login from './components/Auth/Login';
import Register from './components/Auth/Register';
import Dashboard from './components/Dashboard/Dashboard';
import Tickets from './components/Ticket/Tickets';
import TicketDetail from './components/Ticket/TicketDetail';
import ChatLayout from './components/Chat/ChatLayout';
import Leaderboard from './components/Leaderboard/Leaderboard';
import SecuritySettings from './components/Settings/SecuritySettings';
import MFAManagement from './components/Admin/MFAManagement';
import UserManagement from './components/Admin/UserManagement';
import WorkerProfile from './components/WorkerProfile/WorkerProfile';
import './App.css';

function PrivateRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  return user ? children : <Navigate to="/login" />;
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route
              path="/dashboard"
              element={
                <PrivateRoute>
                  <Dashboard />
                </PrivateRoute>
              }
            />
            <Route
              path="/tickets"
              element={
                <PrivateRoute>
                  <Tickets />
                </PrivateRoute>
              }
            />
            <Route
              path="/tickets/:id"
              element={
                <PrivateRoute>
                  <TicketDetail />
                </PrivateRoute>
              }
            />
            <Route
              path="/chat"
              element={
                <PrivateRoute>
                  <ChatLayout />
                </PrivateRoute>
              }
            />
            <Route
              path="/chat/channel/:channelId"
              element={
                <PrivateRoute>
                  <ChatLayout />
                </PrivateRoute>
              }
            />
            <Route
              path="/chat/dm/:dmId"
              element={
                <PrivateRoute>
                  <ChatLayout />
                </PrivateRoute>
              }
            />
            <Route
              path="/leaderboard"
              element={
                <PrivateRoute>
                  <Leaderboard />
                </PrivateRoute>
              }
            />
            <Route
              path="/worker-profile"
              element={
                <PrivateRoute>
                  <WorkerProfile />
                </PrivateRoute>
              }
            />
            <Route
              path="/settings/security"
              element={
                <PrivateRoute>
                  <SecuritySettings />
                </PrivateRoute>
              }
            />
            <Route
              path="/admin/mfa"
              element={
                <PrivateRoute>
                  <MFAManagement />
                </PrivateRoute>
              }
            />
            <Route
              path="/admin/users"
              element={
                <PrivateRoute>
                  <UserManagement />
                </PrivateRoute>
              }
            />
            <Route path="/" element={<Navigate to="/dashboard" />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
