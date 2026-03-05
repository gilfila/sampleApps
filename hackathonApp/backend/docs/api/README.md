# API Documentation

## OpenAPI Specification

The full API specification is available in [openapi.yaml](./openapi.yaml). You can view it
using any OpenAPI-compatible tool such as [Swagger Editor](https://editor.swagger.io/) or
[Redocly](https://redocly.com/).

## Quick Start

### Base URL

- Development: `http://localhost:5000/api`
- Production: `https://hackathon.example.com/api`

### Authentication

The API uses session-based authentication with HTTP-only cookies.

1. **Login**: `POST /api/auth/login` with `{ "email": "...", "password": "..." }`
2. The server sets a `hackathon_session` cookie on success.
3. All subsequent requests must include this cookie (set `withCredentials: true` in axios/fetch).

### MFA Flow

If the user has MFA enabled, the login response will indicate this:

```json
{
  "mfa_required": true,
  "mfa_token": "eyJ...",
  "mfa_token_expires": 300
}
```

Complete login by sending the TOTP code:

```
POST /api/auth/mfa/verify-login
{
  "mfa_token": "eyJ...",
  "totp_code": "123456",
  "remember_device": true
}
```

### Rate Limiting

| Endpoint Category | Limit | Window |
|-------------------|-------|--------|
| `POST /api/auth/login` | 5 requests | per minute per IP |
| `POST /api/auth/register` | 3 requests | per minute per IP |
| `POST /api/auth/mfa/*` | 5 requests | per minute per IP+user |
| `GET /api/*` (authenticated) | 100 requests | per hour per user |
| `POST /api/tickets` | 20 requests | per hour per user |
| WebSocket `send_message` | 50 messages | per minute per user |

When rate-limited, the API returns:

```
HTTP 429 Too Many Requests
Retry-After: 42

{
  "error": "Rate limit exceeded",
  "retry_after": 42
}
```

### Error Response Format

All errors follow a consistent format:

```json
{
  "error": "error_code",
  "message": "Human-readable error description"
}
```

Common HTTP status codes:

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (async operation started) |
| 400 | Bad request / validation error |
| 401 | Not authenticated |
| 403 | Forbidden (insufficient role) |
| 404 | Not found |
| 429 | Rate limited |
| 500 | Server error |
| 503 | Service unavailable (e.g., Workday down) |

## Endpoint Groups

### Auth (`/api/auth/*`)

- `POST /api/auth/login` - Login
- `POST /api/auth/register` - Register
- `POST /api/auth/logout` - Logout
- `POST /api/auth/refresh` - Refresh session
- `GET /api/auth/me` - Get current user

### MFA (`/api/auth/mfa/*`)

- `POST /api/auth/mfa/enroll` - Start MFA enrollment
- `POST /api/auth/mfa/verify-enrollment` - Complete enrollment
- `POST /api/auth/mfa/verify-login` - Verify TOTP during login
- `POST /api/auth/mfa/backup-codes` - Regenerate backup codes
- `DELETE /api/auth/mfa/disable` - Disable MFA

### Chat (`/api/chats/*`)

- `GET /api/chats/channels` - List channels
- `POST /api/chats/channels` - Create channel (admin)
- `POST /api/chats/channels/:id/join` - Join channel
- `GET /api/chats/direct-messages` - List DM conversations
- `POST /api/chats/direct-messages` - Start DM conversation
- `GET /api/chats/:id/messages` - Get messages (paginated)
- `POST /api/chats/:id/mark-read` - Mark as read

### Tickets (`/api/tickets`)

- `GET /api/tickets` - List tickets
- `POST /api/tickets` - Create ticket

### Workers (`/api/workers`)

- `GET /api/workers` - List/search workers

### Admin Sync (`/api/admin/sync/*`)

- `POST /api/admin/sync/user/:workday_id` - Sync single user
- `POST /api/admin/sync/bulk` - Bulk sync
- `GET /api/admin/sync/status/:job_id` - Check job status
- `GET /api/admin/sync/history` - Audit history

### Admin MFA (`/api/admin/mfa/*`)

- `POST /api/admin/mfa/reset/:user_id` - Reset user MFA
- `GET /api/admin/mfa/status` - MFA statistics
- `PUT /api/admin/mfa/enforcement` - Set MFA policy

## WebSocket Events

The application uses Socket.IO for real-time communication. Connect to the
WebSocket server with the session cookie for authentication.

### Client to Server

| Event | Payload | Description |
|-------|---------|-------------|
| `join_conversation` | `{ conversation_id }` | Join a conversation room |
| `leave_conversation` | `{ conversation_id }` | Leave a conversation room |
| `send_message` | `{ conversation_id, content, mentions }` | Send a message |
| `typing_indicator` | `{ conversation_id, is_typing }` | Typing status |
| `mark_read` | `{ conversation_id, last_read_message_id }` | Mark as read |

### Server to Client

| Event | Payload | Description |
|-------|---------|-------------|
| `connected` | `{ user_id, message }` | Connection confirmed |
| `online_users` | `[user_id, ...]` | Initial online user list |
| `presence_update` | `{ user_id, status, timestamp }` | User online/offline |
| `new_message` | `{ id, sender, content, ... }` | New message in room |
| `typing_indicator` | `{ conversation_id, user_id, is_typing }` | Typing status |
| `message_read` | `{ conversation_id, reader_id, ... }` | Read receipt |
| `error` | `{ message, code }` | Error notification |
