# Workstream 1: Chat System Restructure -- Design Document

**Author:** Frontend Architect
**Date:** 2026-02-13
**Status:** DRAFT -- Pending Review
**Target:** Discord/Slack-style chat interface for 1000-concurrent-user hackathon

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Architecture Overview](#2-architecture-overview)
3. [React Component Hierarchy](#3-react-component-hierarchy)
4. [Implementation Plan](#4-implementation-plan)
5. [API Specifications](#5-api-specifications)
6. [Database Schema Changes](#6-database-schema-changes)
7. [WebSocket Event Schema](#7-websocket-event-schema)
8. [Test Cases](#8-test-cases)
9. [Risks and Mitigations](#9-risks-and-mitigations)

---

## 1. Current State Analysis

### 1.1 Current Chat UX Problems

The existing chat component (`frontend/src/components/Chat/Chat.js`) has critical usability issues:

- **Manual ID Entry:** Users must type numeric user IDs, room IDs, and channel IDs into text fields. There is no way to discover or browse channels/users.
- **No Conversation List:** No sidebar showing available channels, groups, or DM threads. Users cannot see what conversations exist.
- **No Presence:** No indication of who is online or offline.
- **No Unread Tracking:** No read receipts or unread badges. Users have no idea if new messages arrived.
- **No Mention System:** No way to @mention users. No autocomplete.
- **Flat Room Model:** Rooms are joined by typing raw string IDs into an input field and clicking "Join Room."
- **Duplicate Messages:** Both `new_message` and `message_sent` events can cause double-rendering on the sender side.
- **No Typing Indicators:** No feedback that another user is composing a message.

### 1.2 Current Technical Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | React 18.2, react-router-dom 6, socket.io-client 4.6 | Create React App, no state library |
| Backend | Flask, Flask-SocketIO, Flask-Login, Flask-CORS | Session-based auth with cookies |
| Database | PostgreSQL (SQLAlchemy ORM) | `chat_messages` table with polymorphic type column |
| Real-time | Socket.IO (WebSocket + polling fallback) | `cors_allowed_origins="*"` |
| Auth | Flask-Login session cookies | `withCredentials: true` on both axios and socket.io |

### 1.3 Current Data Model

The `ChatMessage` model uses a single table with a `message_type` enum (`direct`, `group`, `channel`, `ticket_thread`) and nullable context columns (`thread_id`, `channel_id`, `group_id`, `recipient_id`). There is **no** `Channel`, `ChannelMembership`, `ReadReceipt`, or `UserPresence` table.

### 1.4 Current WebSocket Events

| Event | Direction | Purpose |
|-------|-----------|---------|
| `connect` | Client -> Server | Establishes connection, requires auth |
| `disconnect` | Client -> Server | Cleanup |
| `join_room` | Client -> Server | Join a Socket.IO room by arbitrary string |
| `leave_room` | Client -> Server | Leave a Socket.IO room |
| `send_message` | Client -> Server | Send message, server persists and broadcasts |
| `connected` | Server -> Client | Acknowledgment with user_id |
| `joined_room` | Server -> Client | Acknowledgment |
| `left_room` | Server -> Client | Acknowledgment |
| `new_message` | Server -> Client | Broadcast to room members |
| `message_sent` | Server -> Client | Acknowledgment to sender |
| `error` | Server -> Client | Error notification |

---

## 2. Architecture Overview

### 2.1 Component Architecture Diagram

```
+------------------------------------------------------------------+
|                          App (Router)                              |
|  +------------------------------------------------------------+  |
|  |                    ChatLayout                               |  |
|  |  +----------------+  +----------------------------------+  |  |
|  |  |  ChatSidebar   |  |        ChatMainArea              |  |  |
|  |  |                |  |                                    |  |  |
|  |  | +-----------+  |  |  +-----------------------------+  |  |  |
|  |  | |SearchBar  |  |  |  |     ChatHeader              |  |  |  |
|  |  | +-----------+  |  |  |  (channel name, members,    |  |  |  |
|  |  |                |  |  |   online count)              |  |  |  |
|  |  | +-----------+  |  |  +-----------------------------+  |  |  |
|  |  | |ChannelList|  |  |                                    |  |  |
|  |  | | Channel   |  |  |  +-----------------------------+  |  |  |
|  |  | | Channel   |  |  |  |     MessageList             |  |  |  |
|  |  | | Channel   |  |  |  |  +------------------------+ |  |  |  |
|  |  | +-----------+  |  |  |  | MessageItem            | |  |  |  |
|  |  |                |  |  |  |  avatar, name, time,    | |  |  |  |
|  |  | +-----------+  |  |  |  |  content, reactions     | |  |  |  |
|  |  | |DMList     |  |  |  |  +------------------------+ |  |  |  |
|  |  | | DMItem    |  |  |  |  | MessageItem            | |  |  |  |
|  |  | |  (avatar, |  |  |  |  +------------------------+ |  |  |  |
|  |  | |   name,   |  |  |  |  | ...                    | |  |  |  |
|  |  | |   badge)  |  |  |  +-----------------------------+  |  |  |
|  |  | +-----------+  |  |                                    |  |  |
|  |  |                |  |  +-----------------------------+  |  |  |
|  |  | +-----------+  |  |  | TypingIndicator            |  |  |  |
|  |  | |OnlineUsers|  |  |  +-----------------------------+  |  |  |
|  |  | | Presence  |  |  |                                    |  |  |
|  |  | | Indicator |  |  |  +-----------------------------+  |  |  |
|  |  | +-----------+  |  |  |     MessageComposer         |  |  |  |
|  |  +----------------+  |  |  [input] [mention] [send]   |  |  |  |
|  |                       |  |  +------------------------+ |  |  |  |
|  |                       |  |  | MentionAutocomplete    | |  |  |  |
|  |                       |  |  +------------------------+ |  |  |  |
|  |                       |  +-----------------------------+  |  |  |
|  |                       +----------------------------------+  |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

### 2.2 State Management Approach

The app currently uses React Context for auth (`AuthProvider`). We will extend this pattern with a dedicated `ChatProvider` context rather than introducing Redux, keeping the dependency footprint small.

```
AuthProvider (existing)
  |
  +-- ChatProvider (NEW)
        |
        +-- conversations: Map<id, Conversation>
        +-- activeConversationId: string | null
        +-- messages: Map<conversationId, Message[]>
        +-- unreadCounts: Map<conversationId, number>
        +-- onlineUsers: Set<userId>
        +-- typingUsers: Map<conversationId, Set<userId>>
        +-- connectionStatus: 'connected' | 'disconnected' | 'reconnecting'
```

**Rationale:** The app has ~5 pages and the chat state is localized to one route. Context + useReducer is sufficient and avoids adding a Redux dependency. If the app grows beyond chat, we can migrate to Zustand or Redux later.

### 2.3 WebSocket Event Flow

```
                     CLIENT                                SERVER
                       |                                      |
  [User opens chat] -->|-- connect (with session cookie) ---->|
                       |<-- connected {user_id} --------------|
                       |                                      |
                       |-- get_conversations --------------->|
                       |<-- conversations_list {[...]} -------|
                       |                                      |
                       |-- join_conversation {conv_id} ------>|-- join_room(conv_id)
                       |<-- conversation_joined {conv_id} ----|
                       |                                      |
  [User types] ------->|-- typing_start {conv_id} ---------->|-- broadcast to room
                       |                                      |
  [User sends msg] --->|-- send_message {conv_id, content} ->|-- persist to DB
                       |                                      |-- broadcast to room
                       |<-- new_message {message} ------------|
                       |                                      |
  [Other user sends]   |<-- new_message {message} ------------|
                       |                                      |
  [User reads msgs] -->|-- mark_read {conv_id, msg_id} ----->|-- update read receipt
                       |                                      |-- notify sender
                       |                                      |
  [User goes offline]  |<-- presence_update {user,offline} ---|
                       |                                      |
  [Reconnect] -------->|-- connect --------------------------->|
                       |<-- connected + missed_messages -------|
```

### 2.4 URL Routing Changes

| Current | Proposed | Notes |
|---------|----------|-------|
| `/chat` | `/chat` | Renders ChatLayout with empty state |
| (none) | `/chat/channel/:channelId` | Select a channel |
| (none) | `/chat/dm/:recipientId` | Select a DM conversation |
| (none) | `/chat/thread/:ticketId` | Select a ticket thread |

Using route params lets users share links to conversations and preserves browser history.

---

## 3. React Component Hierarchy

### 3.1 Component Tree

```
ChatLayout
  +-- ChatSidebar
  |     +-- SidebarSearch
  |     +-- ChannelSection
  |     |     +-- SectionHeader ("Channels")
  |     |     +-- ChannelListItem (x N)
  |     |           +-- UnreadBadge (conditional)
  |     +-- DirectMessageSection
  |     |     +-- SectionHeader ("Direct Messages")
  |     |     +-- DMListItem (x N)
  |     |           +-- PresenceIndicator
  |     |           +-- UnreadBadge (conditional)
  |     +-- OnlineUsersSection
  |           +-- SectionHeader ("Online")
  |           +-- UserListItem (x N)
  |                 +-- PresenceIndicator
  +-- ChatMainArea
        +-- ChatHeader
        |     +-- ConversationTitle
        |     +-- MemberCount
        |     +-- OnlineCount
        +-- MessageList
        |     +-- DateDivider (grouped by day)
        |     +-- MessageItem (x N)
        |           +-- UserAvatar
        |           +-- MessageContent
        |           +-- MessageTimestamp
        +-- TypingIndicator
        +-- MessageComposer
              +-- ComposerInput
              +-- MentionAutocomplete (conditional popup)
              +-- SendButton
```

### 3.2 Key Component Specifications

#### ChatLayout

```jsx
// frontend/src/components/Chat/ChatLayout.js
import React from 'react';
import { useParams } from 'react-router-dom';
import { ChatProvider } from '../../contexts/ChatContext';
import ChatSidebar from './ChatSidebar';
import ChatMainArea from './ChatMainArea';
import Navbar from '../Navbar/Navbar';

function ChatLayout() {
  const { conversationType, conversationId } = useParams();

  return (
    <ChatProvider>
      <div>
        <Navbar />
        <div className="chat-layout">
          <ChatSidebar />
          <ChatMainArea
            conversationType={conversationType}
            conversationId={conversationId}
          />
        </div>
      </div>
    </ChatProvider>
  );
}

export default ChatLayout;
```

#### ChatContext (State Management)

```jsx
// frontend/src/contexts/ChatContext.js
import React, { createContext, useContext, useReducer, useEffect, useRef } from 'react';
import { useAuth } from '../services/auth';
import { getSocket, disconnectSocket } from '../services/socket';
import api from '../services/api';

const ChatContext = createContext();

const initialState = {
  channels: [],
  directMessages: [],
  activeConversation: null,
  messages: {},          // { conversationId: Message[] }
  unreadCounts: {},      // { conversationId: number }
  onlineUsers: new Set(),
  typingUsers: {},       // { conversationId: Set<userId> }
  connectionStatus: 'disconnected',
  isLoadingConversations: true,
};

function chatReducer(state, action) {
  switch (action.type) {
    case 'SET_CHANNELS':
      return { ...state, channels: action.payload };
    case 'SET_DIRECT_MESSAGES':
      return { ...state, directMessages: action.payload };
    case 'SET_ACTIVE_CONVERSATION':
      return { ...state, activeConversation: action.payload };
    case 'SET_MESSAGES':
      return {
        ...state,
        messages: {
          ...state.messages,
          [action.conversationId]: action.payload,
        },
      };
    case 'APPEND_MESSAGE': {
      const convId = action.conversationId;
      const existing = state.messages[convId] || [];
      return {
        ...state,
        messages: {
          ...state.messages,
          [convId]: [...existing, action.payload],
        },
      };
    }
    case 'SET_UNREAD_COUNT':
      return {
        ...state,
        unreadCounts: {
          ...state.unreadCounts,
          [action.conversationId]: action.payload,
        },
      };
    case 'SET_ONLINE_USERS':
      return { ...state, onlineUsers: new Set(action.payload) };
    case 'USER_ONLINE':
      return {
        ...state,
        onlineUsers: new Set([...state.onlineUsers, action.payload]),
      };
    case 'USER_OFFLINE': {
      const next = new Set(state.onlineUsers);
      next.delete(action.payload);
      return { ...state, onlineUsers: next };
    }
    case 'SET_TYPING': {
      const convId = action.conversationId;
      const current = state.typingUsers[convId] || new Set();
      const next = new Set(current);
      if (action.isTyping) {
        next.add(action.userId);
      } else {
        next.delete(action.userId);
      }
      return {
        ...state,
        typingUsers: { ...state.typingUsers, [convId]: next },
      };
    }
    case 'SET_CONNECTION_STATUS':
      return { ...state, connectionStatus: action.payload };
    case 'SET_LOADING_CONVERSATIONS':
      return { ...state, isLoadingConversations: action.payload };
    default:
      return state;
  }
}

export function ChatProvider({ children }) {
  const [state, dispatch] = useReducer(chatReducer, initialState);
  const { user } = useAuth();
  const socketRef = useRef(null);

  useEffect(() => {
    if (!user) return;

    const socket = getSocket();
    socketRef.current = socket;

    socket.on('connect', () => {
      dispatch({ type: 'SET_CONNECTION_STATUS', payload: 'connected' });
    });

    socket.on('disconnect', () => {
      dispatch({ type: 'SET_CONNECTION_STATUS', payload: 'disconnected' });
    });

    socket.on('reconnecting', () => {
      dispatch({ type: 'SET_CONNECTION_STATUS', payload: 'reconnecting' });
    });

    socket.on('new_message', (message) => {
      dispatch({
        type: 'APPEND_MESSAGE',
        conversationId: message.conversation_id,
        payload: message,
      });
      // Increment unread if not active conversation
      if (state.activeConversation?.id !== message.conversation_id) {
        dispatch({
          type: 'SET_UNREAD_COUNT',
          conversationId: message.conversation_id,
          payload: (state.unreadCounts[message.conversation_id] || 0) + 1,
        });
      }
    });

    socket.on('presence_update', ({ user_id, status }) => {
      if (status === 'online') {
        dispatch({ type: 'USER_ONLINE', payload: user_id });
      } else {
        dispatch({ type: 'USER_OFFLINE', payload: user_id });
      }
    });

    socket.on('typing_indicator', ({ conversation_id, user_id, is_typing }) => {
      dispatch({
        type: 'SET_TYPING',
        conversationId: conversation_id,
        userId: user_id,
        isTyping: is_typing,
      });
    });

    socket.on('online_users', (userIds) => {
      dispatch({ type: 'SET_ONLINE_USERS', payload: userIds });
    });

    // Load initial data
    loadConversations();

    return () => {
      disconnectSocket();
    };
  }, [user]);

  const loadConversations = async () => {
    dispatch({ type: 'SET_LOADING_CONVERSATIONS', payload: true });
    try {
      const [channelsRes, dmsRes] = await Promise.all([
        api.get('/chats/channels'),
        api.get('/chats/direct-messages'),
      ]);
      dispatch({ type: 'SET_CHANNELS', payload: channelsRes.data.channels });
      dispatch({ type: 'SET_DIRECT_MESSAGES', payload: dmsRes.data.conversations });
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      dispatch({ type: 'SET_LOADING_CONVERSATIONS', payload: false });
    }
  };

  const selectConversation = async (conversation) => {
    dispatch({ type: 'SET_ACTIVE_CONVERSATION', payload: conversation });

    // Join the socket room
    if (socketRef.current) {
      socketRef.current.emit('join_conversation', {
        conversation_id: conversation.id,
      });
    }

    // Load messages
    try {
      const res = await api.get(`/chats/${conversation.id}/messages`);
      dispatch({
        type: 'SET_MESSAGES',
        conversationId: conversation.id,
        payload: res.data.messages,
      });
    } catch (error) {
      console.error('Failed to load messages:', error);
    }

    // Mark as read
    markAsRead(conversation.id);
  };

  const sendMessage = (content, mentions = []) => {
    if (!socketRef.current || !state.activeConversation) return;
    socketRef.current.emit('send_message', {
      conversation_id: state.activeConversation.id,
      content,
      mentions,
    });
  };

  const markAsRead = (conversationId) => {
    if (socketRef.current) {
      socketRef.current.emit('mark_read', { conversation_id: conversationId });
    }
    dispatch({
      type: 'SET_UNREAD_COUNT',
      conversationId,
      payload: 0,
    });
  };

  const sendTypingIndicator = (isTyping) => {
    if (!socketRef.current || !state.activeConversation) return;
    socketRef.current.emit('typing_indicator', {
      conversation_id: state.activeConversation.id,
      is_typing: isTyping,
    });
  };

  const value = {
    ...state,
    selectConversation,
    sendMessage,
    markAsRead,
    sendTypingIndicator,
    loadConversations,
  };

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within ChatProvider');
  }
  return context;
}
```

#### ChatSidebar

```jsx
// frontend/src/components/Chat/ChatSidebar.js (sketch)
import React, { useState } from 'react';
import { useChat } from '../../contexts/ChatContext';

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

  const filteredChannels = channels.filter((ch) =>
    ch.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredDMs = directMessages.filter((dm) =>
    dm.other_user.name.toLowerCase().includes(searchTerm.toLowerCase())
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
          <section className="sidebar-section">
            <h3 className="section-header">Channels</h3>
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
          </section>

          <section className="sidebar-section">
            <h3 className="section-header">Direct Messages</h3>
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
                    onlineUsers.has(dm.other_user.id) ? 'online' : 'offline'
                  }`}
                />
                <span className="item-name">{dm.other_user.name}</span>
                {unreadCounts[dm.id] > 0 && (
                  <span className="unread-badge">{unreadCounts[dm.id]}</span>
                )}
              </button>
            ))}
          </section>
        </>
      )}
    </aside>
  );
}

export default ChatSidebar;
```

#### MessageComposer (with Mention Autocomplete)

```jsx
// frontend/src/components/Chat/MessageComposer.js (sketch)
import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../../contexts/ChatContext';
import api from '../../services/api';

function MessageComposer() {
  const { sendMessage, sendTypingIndicator, activeConversation } = useChat();
  const [text, setText] = useState('');
  const [showMentions, setShowMentions] = useState(false);
  const [mentionQuery, setMentionQuery] = useState('');
  const [mentionResults, setMentionResults] = useState([]);
  const [mentions, setMentions] = useState([]);
  const typingTimeoutRef = useRef(null);
  const inputRef = useRef(null);

  const handleChange = (e) => {
    const value = e.target.value;
    setText(value);

    // Typing indicator with debounce
    sendTypingIndicator(true);
    clearTimeout(typingTimeoutRef.current);
    typingTimeoutRef.current = setTimeout(() => {
      sendTypingIndicator(false);
    }, 2000);

    // Mention detection: find @ followed by characters
    const cursorPos = e.target.selectionStart;
    const textBeforeCursor = value.substring(0, cursorPos);
    const mentionMatch = textBeforeCursor.match(/@(\w*)$/);

    if (mentionMatch) {
      setMentionQuery(mentionMatch[1]);
      setShowMentions(true);
      fetchMentionResults(mentionMatch[1]);
    } else {
      setShowMentions(false);
    }
  };

  const fetchMentionResults = async (query) => {
    if (query.length < 1) return;
    try {
      const res = await api.get('/workers', { params: { search: query, per_page: 8 } });
      setMentionResults(res.data.workers);
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
          placeholder={`Message #${activeConversation.name || 'conversation'}...`}
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
```

### 3.3 New File Structure

```
frontend/src/
  contexts/
    ChatContext.js           (NEW - chat state management)
  components/
    Chat/
      ChatLayout.js          (NEW - replaces Chat.js)
      ChatSidebar.js         (NEW)
      ChatMainArea.js        (NEW)
      ChatHeader.js          (NEW)
      MessageList.js         (NEW)
      MessageItem.js         (NEW)
      MessageComposer.js     (NEW)
      MentionAutocomplete.js (NEW - inline in composer or separate)
      TypingIndicator.js     (NEW)
      PresenceIndicator.js   (NEW)
      UnreadBadge.js         (NEW)
      DateDivider.js         (NEW)
      Chat.js                (DEPRECATED - replaced by ChatLayout.js)
      Chat.css               (REWRITTEN)
      ChatLayout.css         (NEW)
  services/
    socket.js               (MODIFIED - add auth token, reconnection config)
```

---

## 4. Implementation Plan

### Phase 1: Sidebar Navigation and Conversation Model

**Goal:** Replace manual ID entry with a browsable sidebar showing channels and DM conversations.

**Backend changes:**

1. Add `Channel` model to `models.py`
2. Add `ChannelMembership` model
3. Add `Conversation` abstraction layer (helper that normalizes channels, DMs, and ticket threads into a unified conversation concept)
4. Create new blueprint `backend/app/routes/chats.py` with:
   - `GET /api/chats/channels` -- list all channels
   - `GET /api/chats/direct-messages` -- list user's DM conversations
   - `POST /api/chats/channels` -- create a channel (admin)
   - `POST /api/chats/channels/:id/join` -- join a channel
5. Seed default channels: `#general`, `#help-desk`, `#announcements`

**Frontend changes:**

1. Create `ChatContext.js` with `useReducer` state management
2. Create `ChatLayout.js` as new container component
3. Create `ChatSidebar.js` with `ChannelSection` and `DirectMessageSection`
4. Update `App.js` routes: `/chat`, `/chat/channel/:id`, `/chat/dm/:id`
5. Create `ChatLayout.css` with sidebar + main area flexbox layout

**Effort:** 3-4 days

### Phase 2: Refactor Chat Area for Selected Conversation

**Goal:** Display messages for the selected conversation with proper real-time updates.

**Backend changes:**

1. Add `GET /api/chats/:id/messages` endpoint (paginated, cursor-based)
2. Refactor `socketio_handlers.py`:
   - Replace `send_message` handler to use conversation-based routing
   - Add `join_conversation` / `leave_conversation` events
   - Ensure sender does NOT receive duplicate message (remove `message_sent` event; include sender in room broadcast)
3. Add `conversation_id` column to `ChatMessage` (or compute it from type + context fields)

**Frontend changes:**

1. Create `ChatMainArea.js`, `ChatHeader.js`, `MessageList.js`, `MessageItem.js`
2. Create `MessageComposer.js` (replaces inline input)
3. Implement scroll-to-bottom and infinite scroll up for history
4. Add `DateDivider.js` to group messages by day
5. Wire up `selectConversation` flow: join room -> fetch messages -> render

**Effort:** 3-4 days

### Phase 3: Real-time Presence and Unread Tracking

**Goal:** Show who is online and which conversations have unread messages.

**Backend changes:**

1. Add `UserPresence` model (or in-memory Redis/dict for hackathon scale)
2. Add `ReadReceipt` model: `(user_id, conversation_id, last_read_message_id, read_at)`
3. Add WebSocket handlers:
   - `presence_update` broadcast on connect/disconnect
   - `mark_read` handler to persist read receipts
4. Add `GET /api/chats/:id/unread-count` endpoint
5. On connect, emit `online_users` list to the connecting client

**Frontend changes:**

1. Create `PresenceIndicator.js` (green/gray dot)
2. Create `UnreadBadge.js` (pill with count)
3. Wire presence events into `ChatContext`
4. On conversation selection, call `mark_read`
5. Show connection status banner (disconnected / reconnecting)

**Effort:** 2-3 days

### Phase 4: Mentions, Typing Indicators, Polish

**Goal:** @mention autocomplete, typing indicators, and UX polish.

**Backend changes:**

1. Parse `@mentions` in message content server-side, store mention references
2. Add `MessageMention` model: `(message_id, mentioned_user_id)`
3. Add `typing_indicator` WebSocket handler (broadcast to room, exclude sender)
4. (Optional) Send push/notification for @mentions

**Frontend changes:**

1. Create `MentionAutocomplete.js` (dropdown triggered by `@` in composer)
2. Create `TypingIndicator.js` ("Alice is typing...")
3. Highlight @mentions in rendered message content
4. Add keyboard navigation for mention dropdown (arrow keys + enter)
5. Polish: animations, hover states, responsive tweaks

**Effort:** 2-3 days

### Summary

| Phase | Description | Effort | Dependencies |
|-------|------------|--------|-------------|
| 1 | Sidebar Navigation & Conversation Model | 3-4 days | None |
| 2 | Refactored Chat Area | 3-4 days | Phase 1 |
| 3 | Presence & Unread Tracking | 2-3 days | Phase 2 |
| 4 | Mentions & Typing Indicators | 2-3 days | Phase 2 |
| **Total** | | **10-14 days** | |

Phases 3 and 4 can run in parallel once Phase 2 is complete.

---

## 5. API Specifications

### 5.1 New Endpoints

#### GET /api/chats/channels

List all available channels.

**Request:**
```
GET /api/chats/channels
Authorization: session cookie
```

**Response 200:**
```json
{
  "channels": [
    {
      "id": "channel_general",
      "name": "general",
      "description": "General discussion",
      "member_count": 42,
      "is_member": true,
      "unread_count": 3,
      "last_message": {
        "content": "Hello everyone!",
        "sender_name": "Alice Smith",
        "timestamp": "2026-02-13T10:30:00Z"
      }
    }
  ]
}
```

#### GET /api/chats/direct-messages

List the current user's DM conversations.

**Request:**
```
GET /api/chats/direct-messages
Authorization: session cookie
```

**Response 200:**
```json
{
  "conversations": [
    {
      "id": "dm_3_7",
      "type": "direct",
      "other_user": {
        "id": 7,
        "name": "Bob Jones",
        "email": "bob@example.com"
      },
      "unread_count": 1,
      "last_message": {
        "content": "Can you help with table 5?",
        "sender_name": "Bob Jones",
        "timestamp": "2026-02-13T09:15:00Z"
      }
    }
  ]
}
```

#### GET /api/chats/:conversationId/messages

Get paginated messages for a conversation.

**Request:**
```
GET /api/chats/channel_general/messages?before=150&limit=50
Authorization: session cookie
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `before` | int | null | Message ID cursor for pagination (load older messages) |
| `limit` | int | 50 | Messages per page (max 100) |

**Response 200:**
```json
{
  "messages": [
    {
      "id": 149,
      "sender": {
        "id": 3,
        "name": "Alice Smith",
        "email": "alice@example.com"
      },
      "content": "Hello @Bob Jones!",
      "conversation_id": "channel_general",
      "mentions": [{ "id": 7, "name": "Bob Jones" }],
      "timestamp": "2026-02-13T10:29:55Z"
    }
  ],
  "has_more": true
}
```

#### POST /api/chats/:conversationId/mark-read

Mark all messages in a conversation as read up to the latest message.

**Request:**
```
POST /api/chats/channel_general/mark-read
Authorization: session cookie
Content-Type: application/json

{
  "last_read_message_id": 149
}
```

**Response 200:**
```json
{
  "status": "ok",
  "conversation_id": "channel_general",
  "last_read_message_id": 149
}
```

#### POST /api/chats/channels

Create a new channel (admin only).

**Request:**
```
POST /api/chats/channels
Authorization: session cookie
Content-Type: application/json

{
  "name": "team-alpha",
  "description": "Team Alpha coordination"
}
```

**Response 201:**
```json
{
  "id": "channel_team-alpha",
  "name": "team-alpha",
  "description": "Team Alpha coordination",
  "member_count": 1,
  "is_member": true
}
```

#### POST /api/chats/channels/:channelId/join

Join a channel.

**Request:**
```
POST /api/chats/channels/channel_team-alpha/join
Authorization: session cookie
```

**Response 200:**
```json
{
  "status": "joined",
  "channel_id": "channel_team-alpha"
}
```

#### POST /api/chats/direct-messages

Start a new DM conversation (or return existing one).

**Request:**
```
POST /api/chats/direct-messages
Authorization: session cookie
Content-Type: application/json

{
  "recipient_id": 7
}
```

**Response 200:**
```json
{
  "id": "dm_3_7",
  "type": "direct",
  "other_user": {
    "id": 7,
    "name": "Bob Jones",
    "email": "bob@example.com"
  }
}
```

### 5.2 Modified Endpoints

The existing `GET /api/messages` and `POST /api/messages` endpoints remain for backwards compatibility but are **deprecated** in favor of the new `/api/chats/*` routes.

---

## 6. Database Schema Changes

### 6.1 New Tables

#### `channels`

```sql
CREATE TABLE channels (
    id VARCHAR(255) PRIMARY KEY,        -- e.g., "channel_general"
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_by_id INTEGER REFERENCES workers(id),
    is_default BOOLEAN DEFAULT FALSE,   -- auto-join for new users
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_channels_name ON channels(name);
```

#### `channel_memberships`

```sql
CREATE TABLE channel_memberships (
    id SERIAL PRIMARY KEY,
    channel_id VARCHAR(255) NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    joined_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(channel_id, user_id)
);

CREATE INDEX idx_membership_channel ON channel_memberships(channel_id);
CREATE INDEX idx_membership_user ON channel_memberships(user_id);
```

#### `read_receipts`

```sql
CREATE TABLE read_receipts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    conversation_id VARCHAR(255) NOT NULL,   -- "channel_general" or "dm_3_7"
    last_read_message_id INTEGER NOT NULL REFERENCES chat_messages(id),
    read_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, conversation_id)
);

CREATE INDEX idx_read_receipts_user ON read_receipts(user_id);
CREATE INDEX idx_read_receipts_conv ON read_receipts(conversation_id);
```

#### `message_mentions`

```sql
CREATE TABLE message_mentions (
    id SERIAL PRIMARY KEY,
    message_id INTEGER NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
    mentioned_user_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    UNIQUE(message_id, mentioned_user_id)
);

CREATE INDEX idx_mentions_message ON message_mentions(message_id);
CREATE INDEX idx_mentions_user ON message_mentions(mentioned_user_id);
```

### 6.2 Modified Tables

#### `chat_messages` -- Add `conversation_id` column

```sql
ALTER TABLE chat_messages
    ADD COLUMN conversation_id VARCHAR(255);

-- Backfill existing data:
UPDATE chat_messages SET conversation_id =
    CASE
        WHEN message_type = 'channel' THEN 'channel_' || channel_id
        WHEN message_type = 'group' THEN 'group_' || group_id
        WHEN message_type = 'ticket_thread' THEN 'thread_' || thread_id
        WHEN message_type = 'direct' THEN 'dm_' || LEAST(sender_id, recipient_id) || '_' || GREATEST(sender_id, recipient_id)
    END;

CREATE INDEX idx_message_conversation ON chat_messages(conversation_id, timestamp);
```

The `conversation_id` is a denormalized string key that uniquely identifies a conversation regardless of type. This simplifies all query patterns from the frontend perspective.

### 6.3 Presence Tracking

For a hackathon-scale app (1000 users), presence is tracked **in-memory** on the Flask-SocketIO server rather than in the database. This avoids write amplification:

```python
# In-memory presence store (backend/app/services/presence.py)
# Maps user_id -> set of socket session IDs
_online_users = {}  # { user_id: set(sid1, sid2, ...) }

def user_connected(user_id, sid):
    if user_id not in _online_users:
        _online_users[user_id] = set()
    _online_users[user_id].add(sid)

def user_disconnected(user_id, sid):
    if user_id in _online_users:
        _online_users[user_id].discard(sid)
        if not _online_users[user_id]:
            del _online_users[user_id]

def is_online(user_id):
    return user_id in _online_users

def get_online_user_ids():
    return list(_online_users.keys())
```

If the app scales beyond a single process (e.g., multiple Gunicorn workers), presence must move to Redis pub/sub. Flask-SocketIO already supports Redis as a message queue backend.

### 6.4 SQLAlchemy Model Additions

```python
# Add to backend/app/models.py

class Channel(db.Model):
    __tablename__ = 'channels'

    id = db.Column(db.String(255), primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey('workers.id'))
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = db.relationship('Worker', backref='created_channels')
    members = db.relationship('ChannelMembership', backref='channel', lazy='dynamic',
                              cascade='all, delete-orphan')


class ChannelMembership(db.Model):
    __tablename__ = 'channel_memberships'

    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.String(255), db.ForeignKey('channels.id', ondelete='CASCADE'),
                           nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('workers.id', ondelete='CASCADE'),
                        nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('channel_id', 'user_id'),
    )

    user = db.relationship('Worker', backref='channel_memberships')


class ReadReceipt(db.Model):
    __tablename__ = 'read_receipts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('workers.id', ondelete='CASCADE'),
                        nullable=False)
    conversation_id = db.Column(db.String(255), nullable=False)
    last_read_message_id = db.Column(db.Integer, db.ForeignKey('chat_messages.id'),
                                      nullable=False)
    read_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'conversation_id'),
    )


class MessageMention(db.Model):
    __tablename__ = 'message_mentions'

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('chat_messages.id', ondelete='CASCADE'),
                           nullable=False)
    mentioned_user_id = db.Column(db.Integer, db.ForeignKey('workers.id', ondelete='CASCADE'),
                                  nullable=False)

    __table_args__ = (
        db.UniqueConstraint('message_id', 'mentioned_user_id'),
    )
```

---

## 7. WebSocket Event Schema

### 7.1 Client -> Server Events

#### `join_conversation`

Join a conversation's Socket.IO room.

```json
{
  "conversation_id": "channel_general"
}
```

**Server behavior:** Calls `join_room(conversation_id)`. Broadcasts `user_joined_channel` to the room if it is a channel.

#### `leave_conversation`

```json
{
  "conversation_id": "channel_general"
}
```

#### `send_message`

```json
{
  "conversation_id": "channel_general",
  "content": "Hello @Bob Jones! Check this out.",
  "mentions": [{ "id": 7, "name": "Bob Jones" }]
}
```

**Server behavior:** Persists message. Computes `conversation_id` for the DB. Broadcasts `new_message` to the room (including sender). Creates `MessageMention` records.

#### `typing_indicator`

```json
{
  "conversation_id": "channel_general",
  "is_typing": true
}
```

**Server behavior:** Broadcasts `typing_indicator` to the room, excluding the sender.

#### `mark_read`

```json
{
  "conversation_id": "channel_general",
  "last_read_message_id": 149
}
```

**Server behavior:** Upserts `ReadReceipt`. Broadcasts `message_read` to the sender(s) of the messages that were read (for DMs; optional for channels).

### 7.2 Server -> Client Events

#### `connected`

Sent on successful connection.

```json
{
  "user_id": 3,
  "message": "Connected successfully"
}
```

#### `online_users`

Sent immediately after connection with the full list of online user IDs.

```json
[3, 7, 12, 15, 22]
```

#### `presence_update`

Broadcast to all connected clients when a user's online status changes.

```json
{
  "user_id": 7,
  "status": "online",
  "timestamp": "2026-02-13T10:30:00Z"
}
```

#### `new_message`

Broadcast to a conversation room when a new message is sent.

```json
{
  "id": 150,
  "sender": {
    "id": 3,
    "name": "Alice Smith",
    "email": "alice@example.com"
  },
  "content": "Hello @Bob Jones!",
  "conversation_id": "channel_general",
  "mentions": [{ "id": 7, "name": "Bob Jones" }],
  "timestamp": "2026-02-13T10:30:05Z"
}
```

#### `typing_indicator`

Broadcast to conversation room (excluding the sender).

```json
{
  "conversation_id": "channel_general",
  "user_id": 3,
  "user_name": "Alice Smith",
  "is_typing": true
}
```

#### `message_read`

Sent to message senders when their messages are read (primarily for DMs).

```json
{
  "conversation_id": "dm_3_7",
  "reader_id": 7,
  "last_read_message_id": 149,
  "read_at": "2026-02-13T10:31:00Z"
}
```

#### `user_joined_channel`

Broadcast to a channel room when a new user joins.

```json
{
  "channel_id": "channel_general",
  "user": {
    "id": 22,
    "name": "Carol White"
  },
  "timestamp": "2026-02-13T10:32:00Z"
}
```

#### `user_left_channel`

Broadcast to a channel room when a user leaves.

```json
{
  "channel_id": "channel_general",
  "user": {
    "id": 22,
    "name": "Carol White"
  },
  "timestamp": "2026-02-13T10:35:00Z"
}
```

#### `error`

Sent to the triggering client on any error.

```json
{
  "message": "Not authenticated",
  "code": "AUTH_REQUIRED"
}
```

---

## 8. Test Cases

### 8.1 Sidebar Navigation

**TC-1: Display channels in sidebar**

- **Given** the user is authenticated and on the `/chat` route
- **When** the chat layout loads
- **Then** the sidebar displays a "Channels" section with all channels the user is a member of
- **And** each channel shows its name prefixed with `#`

**TC-2: Display DM conversations in sidebar**

- **Given** the user has exchanged direct messages with other users
- **When** the sidebar loads
- **Then** the "Direct Messages" section shows each DM conversation
- **And** each item displays the other user's name and a presence indicator (green=online, gray=offline)

**TC-3: Select a channel**

- **Given** the sidebar shows channel `#general`
- **When** the user clicks on `#general`
- **Then** the URL updates to `/chat/channel/channel_general`
- **And** the main area displays the message history for `#general`
- **And** the sidebar item is visually highlighted as active

**TC-4: Select a DM conversation**

- **Given** the sidebar shows a DM with "Bob Jones"
- **When** the user clicks on "Bob Jones"
- **Then** the URL updates to `/chat/dm/dm_3_7`
- **And** the main area displays the DM history with Bob
- **And** Bob's DM item is highlighted

**TC-5: Search conversations**

- **Given** the sidebar search input is visible
- **When** the user types "gen" into the search field
- **Then** only conversations matching "gen" appear (e.g., `#general`)
- **And** non-matching conversations are hidden

### 8.2 Sending and Receiving Messages

**TC-6: Send a message**

- **Given** the user has selected `#general` as the active conversation
- **When** the user types "Hello team" and presses Enter
- **Then** the message appears in the message list with the user's name and current timestamp
- **And** the input field is cleared

**TC-7: Receive a real-time message**

- **Given** User A has `#general` open
- **When** User B sends a message to `#general`
- **Then** User A sees the message appear at the bottom of the message list without refreshing
- **And** the message list auto-scrolls to the new message

**TC-8: No duplicate messages on send**

- **Given** the user sends a message
- **When** the server broadcasts `new_message` to the room (including sender)
- **Then** the message appears exactly once in the sender's message list
- **And** the old `message_sent` event is no longer emitted

**TC-9: Load older messages (pagination)**

- **Given** a conversation has 200 messages
- **When** the user scrolls to the top of the message list
- **Then** the next batch of 50 older messages is loaded
- **And** the scroll position is preserved (no jump to top)

### 8.3 Presence Updates

**TC-10: User comes online**

- **Given** User A has the chat open
- **When** User B connects to the WebSocket
- **Then** User A receives a `presence_update` event with `status: "online"` for User B
- **And** User B's presence indicator turns green in User A's sidebar

**TC-11: User goes offline**

- **Given** User A sees User B as online
- **When** User B disconnects (closes browser or loses connection)
- **Then** User A receives a `presence_update` event with `status: "offline"` for User B
- **And** User B's presence indicator turns gray

**TC-12: Initial online users list**

- **Given** 15 users are currently online
- **When** User A connects
- **Then** User A receives an `online_users` event with the 15 user IDs
- **And** all 15 users show green presence indicators

### 8.4 Unread Indicators

**TC-13: Unread badge appears**

- **Given** User A is viewing `#general`
- **When** a message arrives in `#help-desk`
- **Then** the `#help-desk` sidebar item shows an unread badge with count "1"

**TC-14: Unread badge increments**

- **Given** `#help-desk` already shows unread count "1"
- **When** another message arrives in `#help-desk`
- **Then** the badge updates to "2"

**TC-15: Unread badge clears on selection**

- **Given** `#help-desk` shows unread count "3"
- **When** the user clicks on `#help-desk`
- **Then** the unread badge disappears
- **And** a `mark_read` event is emitted to the server

### 8.5 Mention Autocomplete

**TC-16: Autocomplete triggers on @**

- **Given** the user is in the message composer
- **When** the user types `@bo`
- **Then** a dropdown appears showing users matching "bo" (e.g., "Bob Jones")

**TC-17: Insert mention**

- **Given** the autocomplete dropdown shows "Bob Jones"
- **When** the user clicks on "Bob Jones"
- **Then** the input text changes to `@Bob Jones ` (with trailing space)
- **And** the dropdown closes
- **And** Bob is tracked in the mentions list for the message

**TC-18: Mention highlight in messages**

- **Given** a message contains `@Bob Jones` in its content
- **When** the message is rendered in the message list
- **Then** `@Bob Jones` is rendered with a highlight/link style (e.g., blue background)

### 8.6 Typing Indicators

**TC-19: Show typing indicator**

- **Given** User A has `#general` open
- **When** User B starts typing in `#general`
- **Then** User A sees "Bob Jones is typing..." below the message list

**TC-20: Typing indicator disappears after timeout**

- **Given** "Bob Jones is typing..." is displayed
- **When** User B stops typing for 3 seconds
- **Then** the typing indicator disappears

**TC-21: Multiple users typing**

- **Given** User B and User C are both typing in `#general`
- **When** User A views `#general`
- **Then** User A sees "Bob Jones and Carol White are typing..."

### 8.7 Error States

**TC-22: WebSocket disconnect**

- **Given** the user has the chat open
- **When** the WebSocket connection drops
- **Then** a banner appears: "Connection lost. Reconnecting..."
- **And** the connection status in ChatContext is set to `'reconnecting'`

**TC-23: WebSocket reconnect**

- **Given** the "Reconnecting..." banner is shown
- **When** the WebSocket successfully reconnects
- **Then** the banner disappears
- **And** the client re-joins the active conversation room
- **And** messages sent during disconnection are fetched via API

**TC-24: API failure loading conversations**

- **Given** the user navigates to `/chat`
- **When** the `GET /api/chats/channels` request fails (500)
- **Then** the sidebar shows an error message: "Failed to load conversations"
- **And** a "Retry" button is displayed

**TC-25: API failure sending message**

- **Given** the WebSocket is disconnected
- **When** the user tries to send a message
- **Then** the message is NOT sent
- **And** a toast/inline error appears: "Unable to send. Check your connection."

---

## 9. Risks and Mitigations

| # | Risk | Impact | Likelihood | Mitigation |
|---|------|--------|------------|------------|
| 1 | **WebSocket scalability at 1000 concurrent users** -- A single Flask-SocketIO process with eventlet/gevent may struggle with 1000 persistent WebSocket connections. | High | Medium | Use `gevent` or `eventlet` async worker (not the default threading mode). If needed, switch to Redis message queue backend for multi-worker deployment. Flask-SocketIO supports this natively with `socketio.init_app(app, message_queue='redis://...')`. Load test with 500+ simulated connections before the event. |
| 2 | **Duplicate messages on sender side** -- Current code emits both `new_message` (room broadcast) and `message_sent` (direct to sender), causing double rendering. | Medium | High (currently happening) | Remove the `message_sent` event. Broadcast `new_message` to the entire room including the sender. Use the message `id` from the server response to deduplicate on the client side as a safety net. |
| 3 | **Session cookie auth with WebSockets** -- Flask-Login session cookies may not be sent correctly in all browsers for WebSocket upgrade requests, especially cross-origin. | High | Medium | Ensure `withCredentials: true` is set on socket.io-client (already done). Test cross-origin cookie behavior. If cookies fail, fall back to passing the session token as a query param during the WebSocket handshake: `io(URL, { auth: { token: sessionId } })`. |
| 4 | **Message ordering during reconnection** -- If a client disconnects and reconnects, messages sent during the gap could be missed. | Medium | Medium | On reconnect, the client should fetch messages since the last known message ID via `GET /api/chats/:id/messages?after=lastMessageId`. Add a `reconnect` handler in `ChatContext` that refetches the current conversation. |
| 5 | **Database write bottleneck for presence** -- Writing user presence status to PostgreSQL on every connect/disconnect creates unnecessary write load. | Medium | Medium | Track presence **in-memory** in the Python process (see Section 6.3). For multi-worker setups, use Redis. Do NOT write presence to PostgreSQL. |
| 6 | **N+1 query on message list** -- Loading messages with sender info can cause N+1 queries if the ORM eagerly loads sender for each message row. | Medium | High | Use `joinedload` or `subqueryload` for the `sender` relationship in the messages query: `ChatMessage.query.options(joinedload(ChatMessage.sender)).filter(...)`. |
| 7 | **Mention autocomplete latency** -- Searching workers on every keystroke creates excessive API calls. | Low | Medium | Debounce the search to 300ms. Cache the workers list client-side (it is unlikely to change during a session). Preload the workers list on chat mount if the total count is under 1000. |
| 8 | **Conversation ID migration** -- Adding `conversation_id` to existing `chat_messages` rows requires a backfill migration. | Low | Low | Write a one-time migration script (Alembic) that computes `conversation_id` from the existing type+context columns. Run it before deploying the new code. The column should be nullable initially, then set to NOT NULL after backfill. |
| 9 | **Browser tab management** -- Users may have multiple tabs open, each with its own WebSocket connection, causing duplicate presence and message handling. | Low | Medium | Allow multiple socket sessions per user (track by `sid`, see Section 6.3). Only mark a user as offline when ALL their sessions disconnect. For message rendering, deduplicate by message `id` on the client. |
| 10 | **Large channel broadcasts** -- A message to `#general` (all 1000 users) triggers 1000 Socket.IO emit calls. | High | Medium | Socket.IO handles room broadcasts efficiently at the transport layer (single write to the event loop, then fan-out). However, if using Redis message queue with multiple workers, each worker re-broadcasts. Limit `#general` to announcements-only if performance degrades. Add message batching (collect messages for 100ms, send as array) as an optimization if needed. |

---

## Appendix A: CSS Specifications for ChatLayout

The main layout uses CSS Flexbox. The sidebar is fixed-width (260px) and the main area fills remaining space.

```css
/* ChatLayout.css */
.chat-layout {
  display: flex;
  height: calc(100vh - 60px); /* subtract navbar height */
  overflow: hidden;
}

.chat-sidebar {
  width: 260px;
  min-width: 260px;
  background: #2f3136;
  color: #dcddde;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.chat-main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #36393f;
  color: #dcddde;
}

/* Sidebar sections */
.sidebar-search {
  padding: 12px;
}

.sidebar-search input {
  width: 100%;
  padding: 8px 12px;
  background: #202225;
  border: none;
  border-radius: 4px;
  color: #dcddde;
  font-size: 14px;
}

.section-header {
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  color: #8e9297;
  letter-spacing: 0.02em;
}

.sidebar-item {
  display: flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 4px;
  margin: 0 8px;
  cursor: pointer;
  background: none;
  border: none;
  color: #8e9297;
  font-size: 15px;
  width: calc(100% - 16px);
  text-align: left;
}

.sidebar-item:hover {
  background: #34373c;
  color: #dcddde;
}

.sidebar-item.active {
  background: #393c43;
  color: #fff;
}

.channel-icon {
  margin-right: 6px;
  font-weight: bold;
  color: #72767d;
}

.item-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Presence indicator */
.presence-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 8px;
  flex-shrink: 0;
}

.presence-dot.online {
  background: #3ba55d;
}

.presence-dot.offline {
  background: #747f8d;
}

/* Unread badge */
.unread-badge {
  background: #ed4245;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 8px;
  min-width: 18px;
  text-align: center;
}

/* Message list */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.message-item {
  display: flex;
  padding: 4px 0;
  margin-bottom: 4px;
}

.message-item:hover {
  background: rgba(4, 4, 5, 0.07);
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #5865f2;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
  margin-right: 12px;
  flex-shrink: 0;
}

.message-body {
  flex: 1;
  min-width: 0;
}

.message-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 2px;
}

.message-author {
  font-weight: 600;
  color: #fff;
}

.message-timestamp {
  font-size: 12px;
  color: #72767d;
}

.message-text {
  color: #dcddde;
  line-height: 1.375;
  word-wrap: break-word;
}

/* Mention highlight */
.mention {
  background: rgba(88, 101, 242, 0.3);
  color: #dee0fc;
  padding: 0 2px;
  border-radius: 3px;
  cursor: pointer;
}

.mention:hover {
  background: #5865f2;
  color: #fff;
}

/* Message composer */
.message-composer {
  padding: 0 16px 16px;
  position: relative;
}

.composer-form {
  display: flex;
  background: #40444b;
  border-radius: 8px;
  padding: 4px;
}

.composer-input {
  flex: 1;
  background: transparent;
  border: none;
  color: #dcddde;
  padding: 8px 12px;
  font-size: 15px;
  outline: none;
}

.composer-send {
  border-radius: 4px;
  padding: 8px 16px;
}

/* Mention autocomplete */
.mention-autocomplete {
  position: absolute;
  bottom: 100%;
  left: 16px;
  right: 16px;
  background: #2f3136;
  border-radius: 8px;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.24);
  max-height: 240px;
  overflow-y: auto;
  margin-bottom: 4px;
}

.mention-option {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  color: #dcddde;
}

.mention-option:hover {
  background: #393c43;
}

.mention-name {
  font-weight: 600;
  margin-right: 8px;
}

.mention-email {
  color: #72767d;
  font-size: 13px;
}

/* Typing indicator */
.typing-indicator {
  padding: 4px 16px;
  font-size: 13px;
  color: #72767d;
  min-height: 24px;
}

/* Date divider */
.date-divider {
  display: flex;
  align-items: center;
  margin: 16px 0;
}

.date-divider::before,
.date-divider::after {
  content: '';
  flex: 1;
  border-bottom: 1px solid #42454a;
}

.date-divider span {
  padding: 0 8px;
  font-size: 12px;
  font-weight: 700;
  color: #72767d;
}

/* Chat header */
.chat-header {
  padding: 12px 16px;
  border-bottom: 1px solid #202225;
  display: flex;
  align-items: center;
  min-height: 48px;
}

.chat-header-title {
  font-weight: 700;
  font-size: 16px;
  color: #fff;
}

.chat-header-meta {
  margin-left: 12px;
  font-size: 13px;
  color: #72767d;
}

/* Connection status banner */
.connection-banner {
  padding: 8px 16px;
  text-align: center;
  font-size: 13px;
  font-weight: 600;
}

.connection-banner.disconnected {
  background: #ed4245;
  color: #fff;
}

.connection-banner.reconnecting {
  background: #faa61a;
  color: #000;
}

/* Empty state */
.chat-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #72767d;
}

.chat-empty-state h2 {
  color: #dcddde;
  margin-bottom: 8px;
}
```

---

## Appendix B: Migration Checklist

- [ ] Create Alembic migration for `channels` table
- [ ] Create Alembic migration for `channel_memberships` table
- [ ] Create Alembic migration for `read_receipts` table
- [ ] Create Alembic migration for `message_mentions` table
- [ ] Create Alembic migration to add `conversation_id` column to `chat_messages`
- [ ] Run backfill script for existing `chat_messages.conversation_id`
- [ ] Seed default channels: `#general`, `#help-desk`, `#announcements`
- [ ] Auto-join all existing users to default channels
- [ ] Update `backend/app/__init__.py` to register new `chats` blueprint
- [ ] Update `frontend/src/App.js` routes for new chat URLs
- [ ] Deprecate (but keep) old `/api/messages` endpoints
- [ ] Test with simulated 100+ WebSocket connections before event
