import React, { useState } from 'react';
import { useChat } from '../../contexts/ChatContext';

function CreateChannelModal({ onClose }) {
  const { createChannel, selectConversation } = useChat();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [channelType, setChannelType] = useState('public');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;

    setError('');
    setLoading(true);

    const result = await createChannel(name, description, channelType);

    if (result.success) {
      selectConversation(result.channel);
      onClose();
    } else {
      setError(result.error);
    }

    setLoading(false);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Create a Channel</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <p className="modal-description">
              Channels are where your team communicates. They're best organized around a topic — #wifi-help, #food, #general.
            </p>

            <div className="modal-field">
              <label htmlFor="channel-name">Name</label>
              <div className="channel-name-input">
                <span className="channel-name-prefix">#</span>
                <input
                  id="channel-name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-'))}
                  placeholder="e.g. wifi-help"
                  maxLength={80}
                  autoFocus
                />
              </div>
            </div>

            <div className="modal-field">
              <label htmlFor="channel-desc">Description <span className="optional">(optional)</span></label>
              <input
                id="channel-desc"
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What's this channel about?"
                maxLength={500}
              />
            </div>

            <div className="modal-field">
              <label>Visibility</label>
              <div className="channel-type-toggle">
                <button
                  type="button"
                  className={`toggle-btn ${channelType === 'public' ? 'active' : ''}`}
                  onClick={() => setChannelType('public')}
                >
                  <span className="toggle-icon">🌐</span>
                  Public
                </button>
                <button
                  type="button"
                  className={`toggle-btn ${channelType === 'private' ? 'active' : ''}`}
                  onClick={() => setChannelType('private')}
                >
                  <span className="toggle-icon">🔒</span>
                  Private
                </button>
              </div>
              <p className="field-hint">
                {channelType === 'public'
                  ? 'Anyone at the hackathon can find and join this channel.'
                  : 'Only invited members can see and join this channel.'}
              </p>
            </div>

            {error && <div className="modal-error">{error}</div>}
          </div>

          <div className="modal-footer">
            <button type="button" className="modal-btn secondary" onClick={onClose}>
              Cancel
            </button>
            <button
              type="submit"
              className="modal-btn primary"
              disabled={loading || !name.trim()}
            >
              {loading ? 'Creating...' : 'Create Channel'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CreateChannelModal;
