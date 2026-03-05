import React from 'react';

function UnreadBadge({ count }) {
  if (!count || count <= 0) return null;

  return (
    <span className="unread-badge">
      {count > 99 ? '99+' : count}
    </span>
  );
}

export default UnreadBadge;
