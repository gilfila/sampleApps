# Workday MCP Server

MCP server that talks to the Workday REST API. It exposes a **get_worker_profile** tool to fetch a worker by employee ID.

Authentication supports two options:

1. **Non-expiring refresh token (recommended)** — Set `WORKDAY_REFRESH_TOKEN_NONEXPIRE` in `.env`. The server uses it to retrieve an access token from the token endpoint (grant_type=refresh_token). Obtain the token once from Workday or via `python exchange_code.py` / `python generate_refresh_token.py`.
2. **Client credentials** — Set `WORKDAY_CLIENT_ID`, `WORKDAY_CLIENT_SECRET`, and `WORKDAY_TOKEN_URL` (tenant token endpoint) to obtain a token from the token endpoint.

## Setup

1. **Create a virtual environment and install dependencies**

   ```bash
   cd workday_mcp_server
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**

   Copy the example env file and set your Workday credentials:

   ```bash
   cp .env.example .env
   # Edit .env with your WORKDAY_* values
   ```

   **Option 1 — Non-expiring refresh token**

   - Set `WORKDAY_CLIENT_ID`, `WORKDAY_CLIENT_SECRET`, `WORKDAY_TOKEN_URL` (e.g. `https://auth.api.workday.com/v1/token`), and `WORKDAY_REFRESH_TOKEN_NONEXPIRE`. The server uses the refresh token to retrieve an access token when calling the API.
   - To obtain a refresh token: run `python generate_refresh_token.py` (or `python exchange_code.py --url-pkce` then `python exchange_code.py <code>`). Add the printed `WORKDAY_REFRESH_TOKEN_NONEXPIRE=...` to your `.env`.

   **Option 2 — Client credentials**

   - `WORKDAY_CLIENT_ID`, `WORKDAY_CLIENT_SECRET`, `WORKDAY_TOKEN_URL` (tenant token endpoint).

   **Required for all**

   - `WORKDAY_API_BASE_URL` — API base (everything before `/staffing`), e.g. `https://api.workday.com`.

## Running the server over stdio

From the `workday_mcp_server` directory:

```bash
python server.py
```

Or with the MCP CLI (if you use `mcp run`):

```bash
uv run mcp run server.py
```

The server uses **stdio** by default: it reads JSON-RPC from stdin and writes responses to stdout. MCP clients (e.g. Claude Desktop, Cursor) start this process and communicate over stdio.

### Example: Cursor / Claude Desktop

In your MCP client config, add a server entry that runs this command:

```json
{
  "workday": {
    "command": "python",
    "args": ["/path/to/hackathonApp/workday_mcp_server/server.py"],
    "cwd": "/path/to/hackathonApp/workday_mcp_server",
    "env": {
      "WORKDAY_CLIENT_ID": "...",
      "WORKDAY_CLIENT_SECRET": "...",
      "WORKDAY_TOKEN_URL": "...",
      "WORKDAY_API_BASE_URL": "..."
    }
  }
}
```

Or rely on `.env` in `cwd` and omit `env`:

```json
{
  "workday": {
    "command": "python",
    "args": ["server.py"],
    "cwd": "/path/to/hackathonApp/workday_mcp_server"
  }
}
```

## Tools

- **get_worker_profile(employee_id)** — Fetches a worker profile from Workday by employee/worker ID. Returns the API response as JSON; errors are returned as JSON with an `error` field.
- **launch_create_ticket_orchestration(reporter, description, status, priority, table_number, assignee?)** — Launches the Workday CreateTicket orchestration. Required: `reporter` (e.g. hacker@hackathon.com), `description`, `status` (e.g. OPEN), `priority` (e.g. HIGH), `table_number` (e.g. 42). Optional: `assignee` (e.g. expert@hackathon.com). Requires `WORKDAY_ORCHESTRATE_BASE_URL` in `.env`.

## API endpoint

The server calls `GET {WORKDAY_API_BASE_URL}/staffing/v7/workers/{employee_id}`. If your tenant uses a different path, change the URL in `server.py` in `_get_worker_from_workday`.
