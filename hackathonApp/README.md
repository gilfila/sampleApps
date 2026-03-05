# Hackathon Messaging & Ticketing Platform

A messaging and ticketing platform for hackathons with up to 1000 participants. **Hacker (participant) data** and **ticket data** are sourced from Workday Extend: each is exposed as a **custom business object (CBO)** and consumed via separate **REST API** URLs.

## Features

- **Workday Integration**: Syncs hacker/participant data from a Workday Extend REST API (custom business object)
- **Ticketing System**: Create, assign, and manage tickets; ticket data comes from a separate Workday Extend REST API (custom business object)
- **Real-time Messaging**: WebSocket-based chat with direct messages, group chats, channels (including default **#General** and **#Get-Help**), and ticket threads
- **Agent / Cursor CLI**: In-app agent in #Get-Help; Settings includes Cursor CLI setup to connect Cursor to the Workday MCP server
- **Expert Management**: Manual expert role assignment with leaderboard tracking
- **Session-based Authentication**: Secure login with Workday email validation (or local/CSV invite list; see SETUP.md)

## Architecture

- **Backend**: Python/Flask with Flask-SocketIO for WebSockets
- **Frontend**: React (to be implemented)
- **Database**: PostgreSQL
- **Deployment**: Render (single web service)

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL
- Workday Integration System User credentials

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Initialize the database:
   ```bash
   python run.py
   # This creates the database tables and seeds default channels (#General, #Get-Help)
   ```

6. Run the application:
   ```bash
   python run.py
   ```

## Configuration

Data is read from two **Workday Extend** custom business objects. URLs are built from a single extensible pattern:

**URL pattern:** `https://api.workday.com/apps/<WORKDAY_APP_NAME>/v1/<collection_name>`

| Source | Description | Environment variable(s) |
|--------|-------------|-------------------------|
| **Hacker / participant data** | Extend CBO for participants | `WORKDAY_EXTEND_BASE_URL` (optional), `WORKDAY_APP_NAME`, `WORKDAY_HACKER_COLLECTION_NAME` — or legacy `WORKDAY_REST_BASE_URL` + `WORKDAY_TENANT` |
| **Ticket data** | Extend CBO for tickets | `WORKDAY_APP_NAME` + `WORKDAY_TICKET_COLLECTION_NAME` (same base URL) — or override with `WORKDAY_TICKETS_BUSINESS_OBJECT_URL` |

See `backend/.env.example` and `workday_mcp_server/.env.example` for full lists.

**Backend** (`backend/.env`):

- `DATABASE_URL` — PostgreSQL connection string  
- `SECRET_KEY` — Flask secret key for sessions  
- **Workday auth:** `WORKDAY_TENANT`, `WORKDAY_CLIENT_ID`, `WORKDAY_CLIENT_SECRET`, `WORKDAY_REFRESH_TOKEN`  
- **Extend URL (extensible):** `WORKDAY_EXTEND_BASE_URL` (default `https://api.workday.com`), `WORKDAY_APP_NAME` — app name used in `/apps/<app>/v1/<collection>`  
- **Hacker data:** `WORKDAY_HACKER_COLLECTION_NAME` — collection name for the participant CBO (URL: `{base}/apps/{app}/v1/{this}`)  
- **Ticket data:** `WORKDAY_TICKET_COLLECTION_NAME` — collection name for the ticket CBO; when set, enables ticket sync and MCP ticket tools  
- **Override (optional):** `WORKDAY_REST_BASE_URL` / `WORKDAY_TENANT` or `WORKDAY_TICKETS_BUSINESS_OBJECT_URL` to use explicit URLs instead of the app+collection pattern  

**Workday MCP Server** (`workday_mcp_server/.env`, e.g. for Cursor/Claude):

- Same Workday auth and Extend vars as above  
- **Hacker/worker:** `WORKDAY_APP_NAME` + `WORKDAY_HACKER_COLLECTION_NAME` (or legacy `WORKDAY_REST_BASE_URL` + `WORKDAY_TENANT`) for `get_worker_profile`  
- **Ticket:** `WORKDAY_APP_NAME` + `WORKDAY_TICKET_COLLECTION_NAME` (or `WORKDAY_TICKETS_BUSINESS_OBJECT_URL`) for MCP tools: `get_tickets`, `get_ticket`, `create_ticket`, `update_ticket`
- **Orchestration:** `WORKDAY_ORCHESTRATE_BASE_URL` (e.g. `https://api.us.wcp.workday.com`) in `workday_mcp_server/.env` — when set, the backend calls the Workday CreateTicket orchestration after each ticket is saved to the local DB (best-effort; ticket creation still succeeds if the orchestration fails).

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `GET /api/auth/me` - Get current user info

### Tickets
- `GET /api/tickets` - Get all tickets (with filtering)
- `GET /api/tickets/<id>` - Get specific ticket
- `POST /api/tickets` - Create ticket
- `PUT /api/tickets/<id>` - Update ticket
- `POST /api/tickets/<id>/assign` - Assign ticket to current user
- `GET /api/tickets/dashboard` - Get dashboard data
- `GET /api/tickets/leaderboard` - Get expert leaderboard

### Messages
- `GET /api/messages` - Get messages (with filtering)
- `POST /api/messages` - Create message
- `GET /api/messages/<id>` - Get specific message

### Agent
- `POST /api/agent/chat` - Send a message to the agent and get a reply (used by in-app #Get-Help and Cursor CLI)

### Workers
- `GET /api/workers` - Get all workers
- `GET /api/workers/<id>` - Get specific worker
- `POST /api/workers/<id>/assign-expert` - Assign expert role (admin only)
- `POST /api/workers/<id>/remove-expert` - Remove expert role (admin only)

## WebSocket Events

- `connect` - Client connection
- `disconnect` - Client disconnection
- `join_room` - Join a room (channel, group, or ticket thread)
- `leave_room` - Leave a room
- `send_message` - Send a message
- `new_message` - Receive a new message
- `message_sent` - Confirmation of sent message

## Default channels and agent

- **#General** and **#Get-Help** are created automatically on first run (seeded on deploy). All users are added to these channels when they register.
- Messages sent in **#Get-Help** are wired to the agent: the agent replies in the same channel.
- To use Workday tools from **Cursor** (e.g. `get_worker_profile`), add the Workday MCP server in **Settings → Cursor CLI / Workday MCP**: follow the instructions and copy the `.cursor/mcp.json` snippet.

## Deployment

The application is configured for deployment on Render. See `render.yaml` for configuration.

## License

MIT
