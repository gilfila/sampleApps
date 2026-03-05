import React, { useRef, useEffect, useState, useCallback } from 'react';
import { useChat } from '../../contexts/ChatContext';
import MessageItem from './MessageItem';
import DateDivider from './DateDivider';

function MessageList() {
  const { activeConversation, messages, loadOlderMessages } = useChat();
  const listRef = useRef(null);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const prevScrollHeightRef = useRef(0);

  const conversationMessages = messages[activeConversation?.id] || [];

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (listRef.current && !loadingOlder) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [conversationMessages.length, loadingOlder]);

  // Reset hasMore when conversation changes
  useEffect(() => {
    setHasMore(true);
  }, [activeConversation?.id]);

  const handleScroll = useCallback(async () => {
    if (!listRef.current || loadingOlder || !hasMore) return;

    if (listRef.current.scrollTop < 50 && conversationMessages.length > 0) {
      setLoadingOlder(true);
      prevScrollHeightRef.current = listRef.current.scrollHeight;

      const firstMessage = conversationMessages[0];
      const result = await loadOlderMessages(activeConversation.id, firstMessage.id);
      setHasMore(result.hasMore);

      // Preserve scroll position after prepending
      requestAnimationFrame(() => {
        if (listRef.current) {
          const newScrollHeight = listRef.current.scrollHeight;
          listRef.current.scrollTop = newScrollHeight - prevScrollHeightRef.current;
        }
      });

      setLoadingOlder(false);
    }
  }, [loadingOlder, hasMore, conversationMessages, activeConversation, loadOlderMessages]);

  // Group messages by date for dividers
  const groupedMessages = [];
  let lastDate = null;

  conversationMessages.forEach((msg) => {
    const msgDate = new Date(msg.timestamp).toDateString();
    if (msgDate !== lastDate) {
      groupedMessages.push({ type: 'divider', date: msg.timestamp });
      lastDate = msgDate;
    }
    groupedMessages.push({ type: 'message', data: msg });
  });

  return (
    <div className="message-list" ref={listRef} onScroll={handleScroll}>
      {loadingOlder && (
        <div className="message-list-loading">Loading older messages...</div>
      )}
      {conversationMessages.length === 0 ? (
        <div className="chat-empty-state">
          <p>No messages yet. Start the conversation!</p>
        </div>
      ) : (
        groupedMessages.map((item, index) => {
          if (item.type === 'divider') {
            return <DateDivider key={`divider-${index}`} date={item.date} />;
          }
          return <MessageItem key={item.data.id} message={item.data} />;
        })
      )}
    </div>
  );
}

export default MessageList;
