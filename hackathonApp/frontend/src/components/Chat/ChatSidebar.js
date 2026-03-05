import React, { useState } from 'react';
import { useChat } from '../../contexts/ChatContext';
import CreateChannelModal from './CreateChannelModal';
import NewMessageModal from './NewMessageModal';
import './ChatModals.css';

function ChatSidebar() {
  const {
    channels,
    directMessages,
    activeConversation,
    unreadCounts,
    onlineUsers,
    selectConversation,
    isLoadingConversations,
  } = useChat();
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateChannel, setShowCreateChannel] = useState(false);
  const [showNewMessage, setShowNewMessage] = useState(false);

  const filteredChannels = channels.filter((ch) =>
    ch.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredDMs = directMessages.filter((dm) =>
    dm.other_user?.name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <aside className="chat-sidebar">
      <div className="sidebar-search">
        <input
          type="text"
          placeholder="Search conversations..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      {isLoadingConversations ? (
        <div className="sidebar-loading">Loading...</div>
      ) : (
        <>
          {/* ---- Channels ---- */}
          <section className="sidebar-section">
            <div className="section-header-row">
              <h3>Channels</h3>
              <button
                className="section-add-btn"
                onClick={() => setShowCreateChannel(true)}
                title="Create a channel"
              >
                +
              </button>
            </div>
            {filteredChannels.map((channel) => (
              <button
                key={channel.id}
                className={`sidebar-item ${
                  activeConversation?.id === channel.id ? 'active' : ''
                }`}
                onClick={() => selectConversation(channel)}
              >
                <span className="channel-icon">#</span>
                <span className="item-name">{channel.name}</span>
                {unreadCounts[channel.id] > 0 && (
                  <span className="unread-badge">{unreadCounts[channel.id]}</span>
                )}
              </button>
            ))}
            {filteredChannels.length === 0 && (
              <div className="sidebar-loading">No channels yet</div>
            )}
          </section>

          {/* ---- Direct Messages ---- */}
          <section className="sidebar-section">
            <div className="section-header-row">
              <h3>Direct Messages</h3>
              <button
                className="section-add-btn"
                onClick={() => setShowNewMessage(true)}
                title="New message"
              >
                +
              </button>
            </div>
            {filteredDMs.map((dm) => (
              <button
                key={dm.id}
                className={`sidebar-item ${
                  activeConversation?.id === dm.id ? 'active' : ''
                }`}
                onClick={() => selectConversation(dm)}
              >
                <span
                  className={`presence-dot ${
                    onlineUsers.has(dm.other_user?.id) ? 'online' : 'offline'
                  }`}
                />
                <span className="item-name">{dm.other_user?.name}</span>
                {unreadCounts[dm.id] > 0 && (
                  <span className="unread-badge">{unreadCounts[dm.id]}</span>
                )}
              </button>
            ))}
            {filteredDMs.length === 0 && (
              <div className="sidebar-loading">No conversations yet</div>
            )}
          </section>
        </>
      )}

      {/* ---- Modals ---- */}
      {showCreateChannel && (
        <CreateChannelModal onClose={() => setShowCreateChannel(false)} />
      )}
      {showNewMessage && (
        <NewMessageModal onClose={() => setShowNewMessage(false)} />
      )}
    </aside>
  );
}

export default ChatSidebar;
