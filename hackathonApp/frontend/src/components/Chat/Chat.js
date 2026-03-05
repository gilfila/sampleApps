import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../services/auth';
import { getSocket, disconnectSocket } from '../../services/socket';
import api from '../../services/api';
import Navbar from '../Navbar/Navbar';
import './Chat.css';

function Chat() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [selectedRoom, setSelectedRoom] = useState(null);
  const [messageType, setMessageType] = useState('direct');
  const [recipientId, setRecipientId] = useState('');
  const messagesEndRef = useRef(null);
  const socketRef = useRef(null);

  useEffect(() => {
    const socket = getSocket();
    socketRef.current = socket;

    socket.on('connect', () => {
      console.log('Connected to server');
    });

    socket.on('new_message', (message) => {
      setMessages((prev) => [message, ...prev]);
    });

    socket.on('message_sent', (message) => {
      setMessages((prev) => [message, ...prev]);
    });

    return () => {
      disconnectSocket();
    };
  }, []);

  useEffect(() => {
    if (selectedRoom) {
      fetchMessages();
    }
  }, [selectedRoom]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchMessages = async () => {
    try {
      const params = {};
      if (messageType === 'direct' && recipientId) {
        params.recipient_id = recipientId;
      } else if (messageType === 'ticket_thread' && selectedRoom) {
        params.thread_id = selectedRoom;
      } else if (messageType === 'channel' && selectedRoom) {
        params.channel_id = selectedRoom;
      } else if (messageType === 'group' && selectedRoom) {
        params.group_id = selectedRoom;
      }

      const response = await api.get('/messages', { params });
      setMessages(response.data.messages.reverse());
    } catch (error) {
      console.error('Error fetching messages:', error);
    }
  };

  const sendMessage = () => {
    if (!newMessage.trim()) return;

    const messageData = {
      content: newMessage,
      message_type: messageType,
      thread_id: messageType === 'ticket_thread' ? selectedRoom : null,
      channel_id: messageType === 'channel' ? selectedRoom : null,
      group_id: messageType === 'group' ? selectedRoom : null,
      recipient_id: messageType === 'direct' ? recipientId : null,
    };

    if (socketRef.current) {
      socketRef.current.emit('send_message', messageData);
    }

    setNewMessage('');
  };

  const joinRoom = (room) => {
    if (socketRef.current) {
      socketRef.current.emit('join_room', { room });
      setSelectedRoom(room);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div>
      <Navbar user={user} onLogout={handleLogout} />
      <div className="container">
        <h1>Chat</h1>
        <div className="chat-container">
          <div className="chat-sidebar">
            <h3>Chat Options</h3>
            <div className="form-group">
              <label>Message Type</label>
              <select value={messageType} onChange={(e) => setMessageType(e.target.value)}>
                <option value="direct">Direct Message</option>
                <option value="channel">Channel</option>
                <option value="group">Group</option>
                <option value="ticket_thread">Ticket Thread</option>
              </select>
            </div>
            {messageType === 'direct' && (
              <div className="form-group">
                <label>Recipient ID</label>
                <input
                  type="number"
                  value={recipientId}
                  onChange={(e) => setRecipientId(e.target.value)}
                  placeholder="Enter recipient user ID"
                />
              </div>
            )}
            {(messageType === 'channel' || messageType === 'group' || messageType === 'ticket_thread') && (
              <div className="form-group">
                <label>Room ID</label>
                <input
                  type="text"
                  value={selectedRoom || ''}
                  onChange={(e) => setSelectedRoom(e.target.value)}
                  placeholder="Enter room ID"
                />
                <button className="btn btn-primary" onClick={() => joinRoom(selectedRoom)}>
                  Join Room
                </button>
              </div>
            )}
          </div>
          <div className="chat-main">
            <div className="chat-messages">
              {messages.length === 0 ? (
                <p>No messages yet</p>
              ) : (
                messages.map((message) => (
                  <div key={message.id} className="message">
                    <div className="message-header">
                      <strong>{message.sender.name}</strong>
                      <span className="message-time">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="message-content">{message.content}</div>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>
            <div className="chat-input">
              <input
                type="text"
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                placeholder="Type a message..."
              />
              <button className="btn btn-primary" onClick={sendMessage}>
                Send
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Chat;
