---
name: workday-api-tools
description: Add or extend Workday API tools (REST and SOAP) in the hackathon app and workday_mcp_server. Use when creating new MCP tools or backend routes that call Workday APIs, or when asked to add a new Workday operation or endpoint.
---

# Workday API Tools Framework

## When to Use This Skill

- Adding a new Workday REST or SOAP operation (e.g. get worker, list workers, update something).
- Adding a new MCP tool that calls Workday.
- Adding or changing a backend route that calls Workday (e.g. `/api/workers/profile`).
- Debugging or changing Workday URL patterns, auth, or env config.

## Layout

| Layer | Location | Purpose |
|-------|----------|--------|
| **Auth** | `workday_mcp_server/workday_auth.py` | Token: refresh token or client credentials; `get_workday_bearer_token()`. |
| **REST** | `workday_mcp_server/workday_rest.py` | REST client: `get_rest_config()`, `rest_request()`, operation helpers (e.g. `get_worker()`). |
| **SOAP** | `workday_mcp_server/workday_soap.py` | SOAP client for WSDL-based operations (e.g. Get_Workers). |
| **Orchestrate** | `workday_mcp_server/workday_orchestrate.py` | Launch orchestrations: `get_orchestrate_config()`, `launch_orchestration()`. |
| **MCP tools** | `workday_mcp_server/server.py` | MCP tool definitions; call REST, SOAP, or Orchestrate and return JSON. |
| **Backend route** | `backend/app/routes/workers.py` | Flask route that loads `workday_mcp_server`, gets token, calls REST or SOAP. |
| **Env** | `workday_mcp_server/.env` | `WORKDAY_*` vars; copy from `.env.example`. |

## REST URL Pattern

CCX REST base and path:

- **Base:** `WORKDAY_REST_BASE_URL` = `https://<host>/ccx/api` (no trailing slash).
- **Tenant:** `WORKDAY_TENANT` = e.g. `hack116_wcpdev1`.
- **Full example:**  
  `{base}/staffing/v7/{tenant}/workers/{worker_id}`  
  → `https://wcpdev-services1.wd101.myworkday.com/ccx/api/staffing/v7/hack116_wcpdev1/workers/3aa5550b7fe348b98d7b5741afc65534`

## Adding a New REST Operation

1. **Env**  
   Ensure `WORKDAY_REST_BASE_URL` and `WORKDAY_TENANT` are in `workday_mcp_server/.env` (see `.env.example`).

2. **`workday_rest.py`**  
   - Add a function that builds path segments and calls `rest_request()`.
   - Path segments = list of strings that form the path after the base (e.g. `["staffing", "v7", tenant, "workers", worker_id]`).
   - Get `tenant` from `get_rest_config()["tenant"]`.
   - Get token in the caller (MCP server or Flask); pass `access_token` into the REST helper.

   Example (get one worker — already present):

   ```python
   def get_worker(worker_id: str, access_token: str) -> dict:
       config = get_rest_config()
       tenant = config["tenant"]
       if not tenant:
           raise ValueError("WORKDAY_TENANT is not set in .env (e.g. hack116_wcpdev1).")
       return rest_request(
           "GET",
           ["staffing", "v7", tenant, "workers", worker_id],
           access_token,
       )
   ```

   Example (new operation — list workers):

   ```python
   def list_workers(access_token: str, limit: int = 100, offset: int = 0) -> dict:
       config = get_rest_config()
       tenant = config["tenant"]
       if not tenant:
           raise ValueError("WORKDAY_TENANT is not set.")
       path = ["staffing", "v7", tenant, "workers"]
       # If API uses query params, add them to URL in rest_request or extend rest_request to accept params
       return rest_request("GET", path, access_token)
   ```

3. **MCP tool (`server.py`)**  
   - Get token with `_ensure_token()`.
   - Call the new REST helper (e.g. `get_worker_rest(...)` or `list_workers_rest(...)`).
   - Return `json.dumps(data, indent=2)` or error JSON.
   - Add `@mcp.tool()` and docstring with Args/Returns.

4. **Backend route (if needed)**  
   In `backend/app/routes/workers.py`, inside `_get_workday_worker_profile`-style logic:
   - Load `workday_mcp_server` env and import `workday_auth`, `workday_rest` (and `workday_soap` if fallback).
   - Get token: `workday_auth.get_workday_bearer_token()`.
   - If REST configured: `workday_rest.get_rest_config()` has `base_url` and `tenant` → call the new `workday_rest` function.
   - Else use SOAP if applicable.

## Adding a New SOAP Operation

1. **WSDL**  
   Use `staffingwsdl.xml` (or `WORKDAY_WSDL_PATH`). Endpoint base comes from WSDL `address location`; strip service/version to get base.

2. **`workday_soap.py`**  
   - Add a function that builds the SOAP envelope (XML), calls the correct endpoint URL, sends POST with `Authorization: Bearer {token}`, and parses the response (e.g. `_parse_get_workers_response`-style).
   - Reuse `get_soap_endpoint_base_from_wsdl()` and build the right path (e.g. `Human_Resources/v42.0` for Get_Workers).

3. **MCP / backend**  
   Same as REST: get token, call the new SOAP helper, return JSON or error.

## Env Vars (Quick Reference)

| Var | Purpose |
|-----|--------|
| `WORKDAY_CLIENT_ID` | OAuth client ID |
| `WORKDAY_CLIENT_SECRET` | OAuth client secret |
| `WORKDAY_TOKEN_URL` | Token endpoint (e.g. `.../ccx/oauth2/<tenant>/token`) |
| `WORKDAY_REFRESH_TOKEN_NONEXPIRE` | Non-expiring refresh token (preferred for token flow) |
| `WORKDAY_REST_BASE_URL` | REST base, e.g. `https://wcpdev-services1.wd101.myworkday.com/ccx/api` |
| `WORKDAY_TENANT` | Tenant name in path, e.g. `hack116_wcpdev1` |
| `WORKDAY_WSDL_PATH` | Optional; SOAP WSDL file path (fallback when REST not set) |
| `WORKDAY_ORCHESTRATE_BASE_URL` | Orchestrate API base (e.g. `https://api.us.wcp.workday.com`) for `launch_create_ticket_orchestration` |
| `WORKDAY_ORCHESTRATE_APP_NAME` | Optional; default app for orchestration launch (default: `hackathontickets_svfbfp`) |

## Checklist for a New Tool

- [ ] Env: add any new vars to `workday_mcp_server/.env.example` and document in this skill.
- [ ] REST: add operation in `workday_rest.py` using `rest_request()` and path segments.
- [ ] MCP: in `server.py`, add `@mcp.tool()` that gets token, calls REST (or SOAP), returns JSON.
- [ ] Backend: if the app must expose it, add route in `backend/app/routes/workers.py` (or a new blueprint), load workday env, call same REST/SOAP helper.
- [ ] Prefer REST when the API supports it (e.g. staffing/v7/...); use SOAP when only WSDL is available.
