-- Migration 004: Chat system tables
-- Adds channels, channel members, read receipts, message mentions,
-- and conversation_id to chat_messages. Aligned with app models: channels.id integer,
-- channel_members (channel_id integer, worker_id). Idempotent for safe re-runs.

-- Channels table (integer id to match existing DB and app Channel model)
CREATE TABLE IF NOT EXISTS channels (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_by_id INTEGER REFERENCES workers(id),
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_channels_name ON channels(name);

-- Channel members (table/columns match app ChannelMember model)
CREATE TABLE IF NOT EXISTS channel_members (
    id SERIAL PRIMARY KEY,
    channel_id INTEGER NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    joined_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(channel_id, worker_id)
);

CREATE INDEX IF NOT EXISTS idx_membership_channel ON channel_members(channel_id);
CREATE INDEX IF NOT EXISTS idx_membership_worker ON channel_members(worker_id);

-- Read receipts
CREATE TABLE IF NOT EXISTS read_receipts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    conversation_id VARCHAR(255) NOT NULL,
    last_read_message_id INTEGER NOT NULL REFERENCES chat_messages(id),
    read_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, conversation_id)
);

CREATE INDEX IF NOT EXISTS idx_read_receipts_user ON read_receipts(user_id);
CREATE INDEX IF NOT EXISTS idx_read_receipts_conv ON read_receipts(conversation_id);

-- Message mentions
CREATE TABLE IF NOT EXISTS message_mentions (
    id SERIAL PRIMARY KEY,
    message_id INTEGER NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
    mentioned_user_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    UNIQUE(message_id, mentioned_user_id)
);

CREATE INDEX IF NOT EXISTS idx_mentions_message ON message_mentions(message_id);
CREATE INDEX IF NOT EXISTS idx_mentions_user ON message_mentions(mentioned_user_id);

-- Add conversation_id to chat_messages (only if missing)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = current_schema() AND table_name = 'chat_messages' AND column_name = 'conversation_id'
  ) THEN
    ALTER TABLE chat_messages ADD COLUMN conversation_id VARCHAR(255);
  END IF;
END $$;

-- Backfill existing data (compare as text to avoid enum literal casting; DB may use CHANNEL vs channel)
UPDATE chat_messages SET conversation_id =
    CASE
        WHEN LOWER(message_type::text) = 'channel' THEN 'channel_' || channel_id
        WHEN LOWER(message_type::text) = 'group' THEN 'group_' || group_id
        WHEN LOWER(message_type::text) = 'ticket_thread' THEN 'thread_' || thread_id
        WHEN LOWER(message_type::text) = 'direct' THEN 'dm_' || LEAST(sender_id, recipient_id) || '_' || GREATEST(sender_id, recipient_id)
    END
WHERE conversation_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_message_conversation ON chat_messages(conversation_id, timestamp);

-- Ensure channels has is_default (existing table may have been created without it)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = 'channels')
     AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'channels' AND column_name = 'is_default') THEN
    ALTER TABLE channels ADD COLUMN is_default BOOLEAN DEFAULT FALSE;
  END IF;
END $$;

-- Seed default channels with integer ids (skip if already present).
-- Only insert when at least one worker exists (created_by_id NOT NULL); DB enum channeltype uses 'PUBLIC'/'PRIVATE'.
INSERT INTO channels (id, name, description, is_default, channel_type, created_by_id)
SELECT v.id, v.name, v.description, v.is_default, v.channel_type::channeltype, w.id
FROM (VALUES
    (1, 'general', 'General discussion', TRUE, 'PUBLIC'),
    (2, 'help-desk', 'Ask for help from experts', TRUE, 'PUBLIC'),
    (3, 'announcements', 'Official announcements', TRUE, 'PUBLIC')
) AS v(id, name, description, is_default, channel_type)
CROSS JOIN (SELECT id FROM workers ORDER BY id LIMIT 1) w
ON CONFLICT (id) DO NOTHING;

-- Auto-join all existing users to default channels (skip existing memberships)
INSERT INTO channel_members (channel_id, worker_id)
SELECT c.id, w.id
FROM channels c
CROSS JOIN workers w
WHERE c.is_default = TRUE
ON CONFLICT (channel_id, worker_id) DO NOTHING;
