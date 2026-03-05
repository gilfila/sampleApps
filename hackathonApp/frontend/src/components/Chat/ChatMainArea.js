import React, { useState } from 'react';
import { useChat } from '../../contexts/ChatContext';
import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import TypingIndicator from './TypingIndicator';
import MessageComposer from './MessageComposer';
import CreateChannelModal from './CreateChannelModal';
import NewMessageModal from './NewMessageModal';
import './ChatModals.css';

function GetStarted() {
  const [showCreateChannel, setShowCreateChannel] = useState(false);
  const [showNewMessage, setShowNewMessage] = useState(false);

  return (
    <div className="get-started">
      <div className="get-started-icon">💬</div>
      <h2>Welcome to Hackathon Chat</h2>
      <p>
        Connect with fellow hackers, ask questions in channels, or send a direct
        message to a teammate. Pick an option below to get started!
      </p>
      <div className="get-started-actions">
        <button
          className="get-started-btn"
          onClick={() => setShowCreateChannel(true)}
        >
          <span className="get-started-btn-icon">#</span>
          Create a Channel
        </button>
        <button
          className="get-started-btn"
          onClick={() => setShowNewMessage(true)}
        >
          <span className="get-started-btn-icon">✉️</span>
          Send a Message
        </button>
      </div>

      {showCreateChannel && (
        <CreateChannelModal onClose={() => setShowCreateChannel(false)} />
      )}
      {showNewMessage && (
        <NewMessageModal onClose={() => setShowNewMessage(false)} />
      )}
    </div>
  );
}

function ChatMainArea() {
  const { activeConversation, connectionStatus } = useChat();

  return (
    <div className="chat-main-area">
      {connectionStatus === 'disconnected' && (
        <div className="connection-banner disconnected">
          Connection lost. Reconnecting...
        </div>
      )}
      {connectionStatus === 'reconnecting' && (
        <div className="connection-banner reconnecting">
          Reconnecting...
        </div>
      )}

      {activeConversation ? (
        <>
          <ChatHeader />
          <MessageList />
          <TypingIndicator />
          <MessageComposer />
        </>
      ) : (
        <GetStarted />
      )}
    </div>
  );
}

export default ChatMainArea;
