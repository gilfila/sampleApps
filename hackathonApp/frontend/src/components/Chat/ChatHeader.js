import React from 'react';
import { useChat } from '../../contexts/ChatContext';

function ChatHeader() {
  const { activeConversation } = useChat();

  if (!activeConversation) return null;

  const isChannel = activeConversation.id?.startsWith('channel_');
  const name = isChannel
    ? `# ${activeConversation.name}`
    : activeConversation.other_user?.name || activeConversation.name || 'Conversation';

  return (
    <div className="chat-header">
      <span className="chat-header-title">{name}</span>
      {activeConversation.member_count && (
        <span className="chat-header-meta">
          {activeConversation.member_count} members
        </span>
      )}
      {activeConversation.description && (
        <span className="chat-header-meta">
          {activeConversation.description}
        </span>
      )}
    </div>
  );
}

export default ChatHeader;
