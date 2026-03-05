import React, { useState, useEffect, useRef } from 'react';
import { useChat } from '../../contexts/ChatContext';
import api from '../../services/api';

function NewMessageModal({ onClose }) {
  const { createDirectMessage, selectConversation } = useChat();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef(null);
  const debounceRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (query.trim().length < 1) {
      setResults([]);
      return;
    }

    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      searchUsers(query.trim());
    }, 250);

    return () => clearTimeout(debounceRef.current);
  }, [query]);

  const searchUsers = async (q) => {
    setLoading(true);
    try {
      const res = await api.get('/chats/users/search', { params: { q, limit: 15 } });
      setResults(res.data.users || []);
    } catch (err) {
      console.error('User search failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectUser = async (user) => {
    setError('');
    const result = await createDirectMessage(user.id);
    if (result.success) {
      selectConversation(result.conversation);
      onClose();
    } else {
      setError(result.error);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>New Message</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body">
          <p className="modal-description">
            Find a hackathon participant to start a conversation with.
          </p>

          <div className="modal-field">
            <label htmlFor="user-search">To:</label>
            <input
              id="user-search"
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by name or email..."
              autoComplete="off"
            />
          </div>

          {error && <div className="modal-error">{error}</div>}

          <div className="user-search-results">
            {loading && <div className="search-loading">Searching...</div>}

            {!loading && query.length > 0 && results.length === 0 && (
              <div className="search-empty">No participants found for "{query}"</div>
            )}

            {results.map((user) => (
              <button
                key={user.id}
                className="user-result-item"
                onClick={() => handleSelectUser(user)}
              >
                <div className="user-result-avatar">
                  {(user.name || '?').split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)}
                </div>
                <div className="user-result-info">
                  <span className="user-result-name">{user.name}</span>
                  <span className="user-result-email">{user.email}</span>
                  {user.team_name && (
                    <span className="user-result-team">Team: {user.team_name}</span>
                  )}
                </div>
                <span className="user-result-role">{user.role}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="modal-footer">
          <button type="button" className="modal-btn secondary" onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

export default NewMessageModal;
