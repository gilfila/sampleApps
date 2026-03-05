import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../services/auth';
import { ChatProvider } from '../../contexts/ChatContext';
import ChatSidebar from './ChatSidebar';
import ChatMainArea from './ChatMainArea';
import Navbar from '../Navbar/Navbar';
import './ChatLayout.css';

function ChatLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <ChatProvider>
      <div>
        <Navbar user={user} onLogout={handleLogout} />
        <div className="chat-layout">
          <ChatSidebar />
          <ChatMainArea />
        </div>
      </div>
    </ChatProvider>
  );
}

export default ChatLayout;
