import React from 'react';

function getInitials(name) {
  if (!name) return '?';
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function formatTimestamp(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function renderContent(content, mentions) {
  if (!mentions || mentions.length === 0) {
    return content;
  }

  // Highlight @mentions in message content
  let parts = [content];
  mentions.forEach((mention) => {
    const newParts = [];
    parts.forEach((part) => {
      if (typeof part !== 'string') {
        newParts.push(part);
        return;
      }
      const mentionText = `@${mention.name}`;
      const splitParts = part.split(mentionText);
      splitParts.forEach((sp, i) => {
        if (i > 0) {
          newParts.push(
            <span key={`mention-${mention.id}-${i}`} className="mention">
              {mentionText}
            </span>
          );
        }
        if (sp) newParts.push(sp);
      });
    });
    parts = newParts;
  });

  return parts;
}

function MessageItem({ message }) {
  const senderName = message.sender?.name || 'Unknown';

  return (
    <div className="message-item">
      <div className="message-avatar">
        {getInitials(senderName)}
      </div>
      <div className="message-body">
        <div className="message-header">
          <span className="message-author">{senderName}</span>
          <span className="message-timestamp">
            {formatTimestamp(message.timestamp)}
          </span>
        </div>
        <div className="message-text">
          {renderContent(message.content, message.mentions)}
        </div>
      </div>
    </div>
  );
}

export default MessageItem;
