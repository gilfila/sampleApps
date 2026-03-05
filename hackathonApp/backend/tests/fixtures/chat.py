"""Chat test data fixtures."""

CHANNEL_MESSAGE = {
    'content': 'Hello team!',
    'message_type': 'channel',
    'channel_id': 'channel_general',
}

DIRECT_MESSAGE = {
    'content': 'Hey, how are you?',
    'message_type': 'direct',
    'recipient_id': 2,
}

TICKET_THREAD_MESSAGE = {
    'content': 'Working on this ticket now.',
    'message_type': 'ticket_thread',
    'thread_id': 1,
}

GROUP_MESSAGE = {
    'content': 'Group discussion update.',
    'message_type': 'group',
    'group_id': 'group_alpha_team',
}

XSS_PAYLOADS = [
    '<script>alert("xss")</script>Normal text',
    '<img onerror=alert(1) src=x>',
    '<svg onload=alert(1)>',
    'javascript:alert(1)',
    '<a href="javascript:alert(1)">click</a>',
    '<div onmouseover="alert(1)">hover</div>',
    '"><script>alert(document.cookie)</script>',
]

LONG_MESSAGE = 'A' * 10001  # Exceeds max_length default of 10000

EMPTY_MESSAGES = [
    '',
    '   ',
    None,
]

DEFAULT_CHANNELS = [
    'channel_general',
    'channel_help_desk',
    'channel_announcements',
]


def bulk_messages(count=200, sender_id=1, channel_id='channel_general'):
    """Generate bulk messages for pagination testing."""
    return [
        {
            'content': f'Message {i} in {channel_id}',
            'message_type': 'channel',
            'channel_id': channel_id,
            'sender_id': sender_id,
        }
        for i in range(1, count + 1)
    ]
