import React from 'react';

function PresenceIndicator({ isOnline }) {
  return (
    <span className={`presence-dot ${isOnline ? 'online' : 'offline'}`} />
  );
}

export default PresenceIndicator;
