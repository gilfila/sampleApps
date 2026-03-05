import React, { createContext, useContext, useReducer, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../services/auth';
import { getSocket, disconnectSocket } from '../services/socket';
import api from '../services/api';

const ChatContext = createContext();

const initialState = {
  channels: [],
  directMessages: [],
  activeConversation: null,
  messages: {},
  unreadCounts: {},
  onlineUsers: new Set(),
  typingUsers: {},
  connectionStatus: 'disconnected',
  isLoadingConversations: true,
};

function chatReducer(state, action) {
  switch (action.type) {
    case 'SET_CHANNELS':
      return { ...state, channels: action.payload };
    case 'ADD_CHANNEL': {
      // Deduplicate
      if (state.channels.some((ch) => ch.id === action.payload.id)) return state;
      return { ...state, channels: [...state.channels, action.payload] };
    }
    case 'SET_DIRECT_MESSAGES':
      return { ...state, directMessages: action.payload };
    case 'ADD_DIRECT_MESSAGE': {
      if (state.directMessages.some((dm) => dm.id === action.payload.id)) return state;
      return { ...state, directMessages: [action.payload, ...state.directMessages] };
    }
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
      if (existing.some((m) => m.id === action.payload.id)) return state;
      return {
        ...state,
        messages: {
          ...state.messages,
          [convId]: [...existing, action.payload],
        },
      };
    }
    case 'PREPEND_MESSAGES': {
      const convId = action.conversationId;
      const existing = state.messages[convId] || [];
      return {
        ...state,
        messages: {
          ...state.messages,
          [convId]: [...action.payload, ...existing],
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
        next.add(action.userName || action.userId);
      } else {
        next.delete(action.userName || action.userId);
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
  const stateRef = useRef(state);
  stateRef.current = state;

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
      const convId = message.conversation_id;
      if (!convId) return;
      dispatch({
        type: 'APPEND_MESSAGE',
        conversationId: convId,
        payload: message,
      });
      const current = stateRef.current;
      if (current.activeConversation?.id !== convId) {
        dispatch({
          type: 'SET_UNREAD_COUNT',
          conversationId: convId,
          payload: (current.unreadCounts[convId] || 0) + 1,
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

    socket.on('typing_indicator', ({ conversation_id, user_id, user_name, is_typing }) => {
      dispatch({
        type: 'SET_TYPING',
        conversationId: conversation_id,
        userId: user_id,
        userName: user_name || user_id,
        isTyping: is_typing,
      });
    });

    socket.on('online_users', (userIds) => {
      dispatch({ type: 'SET_ONLINE_USERS', payload: userIds });
    });

    loadConversations();

    return () => {
      disconnectSocket();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  // ----- Data loaders -----

  const loadConversations = async () => {
    dispatch({ type: 'SET_LOADING_CONVERSATIONS', payload: true });
    try {
      const [channelsRes, dmsRes] = await Promise.all([
        api.get('/chats/channels'),
        api.get('/chats/direct-messages'),
      ]);
      dispatch({ type: 'SET_CHANNELS', payload: channelsRes.data.channels || [] });
      dispatch({ type: 'SET_DIRECT_MESSAGES', payload: dmsRes.data.conversations || [] });
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      dispatch({ type: 'SET_LOADING_CONVERSATIONS', payload: false });
    }
  };

  // ----- Conversation selection -----

  const selectConversation = async (conversation) => {
    dispatch({ type: 'SET_ACTIVE_CONVERSATION', payload: conversation });

    if (socketRef.current) {
      socketRef.current.emit('join_conversation', {
        conversation_id: conversation.id,
      });
    }

    try {
      const res = await api.get(`/chats/${conversation.id}/messages`);
      dispatch({
        type: 'SET_MESSAGES',
        conversationId: conversation.id,
        payload: res.data.messages || [],
      });
    } catch (error) {
      console.error('Failed to load messages:', error);
    }

    markAsRead(conversation.id);
  };

  const loadOlderMessages = useCallback(async (conversationId, beforeMessageId) => {
    try {
      const res = await api.get(`/chats/${conversationId}/messages`, {
        params: { before: beforeMessageId, limit: 50 },
      });
      const older = res.data.messages || [];
      if (older.length > 0) {
        dispatch({
          type: 'PREPEND_MESSAGES',
          conversationId,
          payload: older,
        });
      }
      return { hasMore: res.data.has_more };
    } catch (error) {
      console.error('Failed to load older messages:', error);
      return { hasMore: false };
    }
  }, []);

  // ----- Sending -----

  const sendMessage = (content, mentions = []) => {
    if (!socketRef.current || !state.activeConversation) return;
    socketRef.current.emit('send_message', {
      conversation_id: state.activeConversation.id,
      content,
      mentions,
    });
  };

  // ----- Unread / typing -----

  const markAsRead = (conversationId) => {
    if (socketRef.current) {
      socketRef.current.emit('mark_read', { conversation_id: conversationId });
    }
    dispatch({ type: 'SET_UNREAD_COUNT', conversationId, payload: 0 });
  };

  const sendTypingIndicator = (isTyping) => {
    if (!socketRef.current || !state.activeConversation) return;
    socketRef.current.emit('typing_indicator', {
      conversation_id: state.activeConversation.id,
      is_typing: isTyping,
    });
  };

  // ----- Create channel -----

  const createChannel = async (name, description = '', channelType = 'public') => {
    try {
      const res = await api.post('/chats/channels', {
        name,
        description,
        channel_type: channelType,
      });
      const newChannel = res.data.channel;
      dispatch({ type: 'ADD_CHANNEL', payload: newChannel });

      // Auto-join the socket room
      if (socketRef.current) {
        socketRef.current.emit('join_conversation', { conversation_id: newChannel.id });
      }

      return { success: true, channel: newChannel };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to create channel',
      };
    }
  };

  // ----- Create / get DM -----

  const createDirectMessage = async (targetUserId) => {
    try {
      const res = await api.post('/chats/direct-messages', {
        target_user_id: targetUserId,
      });
      const convo = res.data.conversation;
      dispatch({ type: 'ADD_DIRECT_MESSAGE', payload: convo });

      // Auto-join the socket room
      if (socketRef.current) {
        socketRef.current.emit('join_conversation', { conversation_id: convo.id });
      }

      return { success: true, conversation: convo };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to start conversation',
      };
    }
  };

  // ----- Exposed value -----

  const value = {
    ...state,
    selectConversation,
    sendMessage,
    markAsRead,
    sendTypingIndicator,
    loadConversations,
    loadOlderMessages,
    createChannel,
    createDirectMessage,
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
