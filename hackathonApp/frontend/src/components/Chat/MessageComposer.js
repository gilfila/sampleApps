import React, { useState, useRef } from 'react';
import { useChat } from '../../contexts/ChatContext';
import api from '../../services/api';

function MessageComposer() {
  const { sendMessage, sendTypingIndicator, activeConversation } = useChat();
  const [text, setText] = useState('');
  const [showMentions, setShowMentions] = useState(false);
  const [mentionResults, setMentionResults] = useState([]);
  const [mentions, setMentions] = useState([]);
  const typingTimeoutRef = useRef(null);
  const inputRef = useRef(null);
  const fetchTimeoutRef = useRef(null);

  const handleChange = (e) => {
    const value = e.target.value;
    setText(value);

    // Typing indicator with debounce
    sendTypingIndicator(true);
    clearTimeout(typingTimeoutRef.current);
    typingTimeoutRef.current = setTimeout(() => {
      sendTypingIndicator(false);
    }, 2000);

    // Mention detection
    const cursorPos = e.target.selectionStart;
    const textBeforeCursor = value.substring(0, cursorPos);
    const mentionMatch = textBeforeCursor.match(/@(\w*)$/);

    if (mentionMatch) {
      setShowMentions(true);
      // Debounce the API call
      clearTimeout(fetchTimeoutRef.current);
      fetchTimeoutRef.current = setTimeout(() => {
        fetchMentionResults(mentionMatch[1]);
      }, 300);
    } else {
      setShowMentions(false);
    }
  };

  const fetchMentionResults = async (query) => {
    if (query.length < 1) return;
    try {
      const res = await api.get('/workers', { params: { search: query, per_page: 8 } });
      setMentionResults(res.data.workers || []);
    } catch (err) {
      console.error('Mention search failed:', err);
    }
  };

  const insertMention = (user) => {
    const cursorPos = inputRef.current.selectionStart;
    const textBeforeCursor = text.substring(0, cursorPos);
    const textAfterCursor = text.substring(cursorPos);
    const newTextBefore = textBeforeCursor.replace(/@\w*$/, `@${user.name} `);
    setText(newTextBefore + textAfterCursor);
    setMentions([...mentions, { id: user.id, name: user.name }]);
    setShowMentions(false);
    inputRef.current.focus();
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    sendMessage(text, mentions);
    setText('');
    setMentions([]);
    sendTypingIndicator(false);
    clearTimeout(typingTimeoutRef.current);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      handleSubmit(e);
    }
  };

  if (!activeConversation) return null;

  return (
    <div className="message-composer">
      {showMentions && mentionResults.length > 0 && (
        <div className="mention-autocomplete">
          {mentionResults.map((user) => (
            <button
              key={user.id}
              className="mention-option"
              onClick={() => insertMention(user)}
            >
              <span className="mention-name">{user.name}</span>
              <span className="mention-email">{user.email}</span>
            </button>
          ))}
        </div>
      )}
      <form onSubmit={handleSubmit} className="composer-form">
        <input
          ref={inputRef}
          type="text"
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={`Message ${activeConversation.name ? '#' + activeConversation.name : activeConversation.other_user?.name || 'conversation'}...`}
          className="composer-input"
        />
        <button type="submit" className="btn btn-primary composer-send">
          Send
        </button>
      </form>
    </div>
  );
}

export default MessageComposer;
