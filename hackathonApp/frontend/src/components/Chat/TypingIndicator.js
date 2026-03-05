import React from 'react';
import { useChat } from '../../contexts/ChatContext';

function TypingIndicator() {
  const { activeConversation, typingUsers } = useChat();

  if (!activeConversation) return null;

  const typing = typingUsers[activeConversation.id];
  if (!typing || typing.size === 0) {
    return <div className="typing-indicator" />;
  }

  const names = Array.from(typing);

  let text = '';
  if (names.length === 1) {
    text = `${names[0]} is typing...`;
  } else if (names.length === 2) {
    text = `${names[0]} and ${names[1]} are typing...`;
  } else {
    text = 'Several people are typing...';
  }

  return <div className="typing-indicator">{text}</div>;
}

export default TypingIndicator;
