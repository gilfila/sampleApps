# Hackathon App — End-to-End Flow (E2E Test Walkthrough)

This document walks through the **entire application flow from the end user’s perspective**. Every step describes what the user does in the app (navigate, click, type, select) and what they see as a result. Use it for manual verification or to drive E2E tests.

**Conventions:**
- **Major version** (e.g. **1.0**, **2.0**) = large feature area (Auth, MFA, Ticketing, Chat, etc.).
- **Minor version** (e.g. **1.1**, **1.2**) = specific sub-feature or user journey within that area.
- **Steps** within each subsection are lettered (e.g. **1.1.a**, **7.2.b**). Users never call backend services directly; all verification is done through the UI.
- **Verified**: Mark each step with `[x]` when you have confirmed it works; leave as `[ ]` until then.

---

## 1.0 Authentication

### 1.1 Registration

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 1.1.a | User opens the app and clicks or navigates to **Register** (e.g. from a “Register” link or `/register`). | Register page appears with fields: Name, Email, Password. |
| [ ] | 1.1.b | User enters an **email that is not in the system** (not in synced workers) and submits the form. | An error message appears, e.g. “Email not found. Please contact admin.” |
| [ ] | 1.1.c | User enters an **email that is already registered** (has a password) and submits. | An error message appears, e.g. “User already registered.” |
| [ ] | 1.1.d | User enters a valid **Workday email** (in system, not yet registered), name, and password (min 8 characters) and submits. | Registration succeeds; user is taken to the **Login** page. |
| [ ] | 1.1.e | User completes registration and is redirected. | User lands on Login page and can sign in with the new account. |

### 1.2 Login (password only)

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 1.2.a | User opens **Login** (e.g. via “Login” link or `/login`). | Login page with Email and Password fields. |
| [ ] | 1.2.b | User enters wrong email or wrong password and submits. | An error message appears, e.g. “Invalid credentials”; user remains on Login. |
| [ ] | 1.2.c | User enters correct email and password (account active) and submits. | User is signed in and redirected to the **Dashboard** (or default post-login page). |
| [ ] | 1.2.d | User enters correct credentials but the account is disabled, then submits. | An error message appears, e.g. “Account is disabled”; user is not signed in. |

### 1.3 Logout

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 1.3.a | Logged-in user clicks **Logout** in the navbar (or equivalent). | User is signed out and redirected to the **Login** page; session is cleared. |

### 1.4 Session and current user

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 1.4.a | User is logged in and opens a private page (e.g. **Dashboard**). | Page loads normally; user sees their dashboard (or that page) with their identity/name visible. |
| [ ] | 1.4.b | User’s session has expired or they open the app in a new tab without a valid session, then try to open a private page. | App redirects them to the **Login** page (they do not see the private content). |

---

## 2.0 MFA (Multi-Factor Authentication)

### 2.1 MFA enrollment (from Settings)

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 2.1.a | Logged-in user opens **Settings** and goes to **Security** (e.g. `/settings/security` or Settings → Security). | Security settings page opens; MFA status is shown (e.g. “MFA disabled”). |
| [ ] | 2.1.b | User clicks **Enable MFA** (or similar). | App shows a QR code and/or a manual key to enter into an authenticator app. |
| [ ] | 2.1.c | User adds the account in their authenticator app, then enters the 6-digit code in the app and submits. | App confirms MFA is enabled and shows **backup codes** (one-time); user is told to save them. |
| [ ] | 2.1.d | User returns to Settings → Security. | Security page shows “MFA enabled” (or equivalent). |

### 2.2 MFA at login (when MFA is enabled)

*If the app does not yet show an MFA step after password login, treat these as design steps until that flow is implemented.*

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 2.2.a | User with MFA enabled enters correct email and password on Login and submits. | App does not log them in yet; a second step appears asking for the **verification code** (and optionally “Remember this device”). |
| [ ] | 2.2.b | User enters the current 6-digit code from their authenticator app and optionally checks “Remember this device,” then submits. | User is logged in and redirected to the Dashboard (or default post-login page). |
| [ ] | 2.2.c | User enters an **invalid or expired** verification code and submits. | An error message appears, e.g. “Invalid verification code”; user can try again. |
| [ ] | 2.2.d | User enters a **backup code** instead of the TOTP code (where the UI allows it) and submits. | Login succeeds; that backup code is consumed and no longer works. |
| [ ] | 2.2.e | User logs in from a device they previously marked “Remember this device.” | App may skip the MFA code step and log them in directly (if implemented). |

### 2.3 MFA disable (from Settings)

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 2.3.a | User goes to Settings → Security and clicks **Disable MFA**. | A form or modal appears asking for current password and current TOTP code. |
| [ ] | 2.3.b | User enters correct password and current TOTP code and submits. | MFA is disabled; Security page shows “MFA disabled” (or equivalent). |

### 2.4 Backup codes

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 2.4.a | In Settings → Security, user clicks **Regenerate backup codes** (or similar). | App may ask for password; then shows a new set of backup codes (one-time). User can copy or save them. |

### 2.5 Trusted devices (optional)

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 2.5.a | User completes MFA login with “Remember this device” checked. | Login succeeds; on a future login from the same device, app may skip MFA (if implemented). |
| [ ] | 2.5.b | User goes to Settings and opens **Trusted devices** (if available). | List of trusted devices is shown; user can revoke individual devices. |

### 2.6 Admin MFA management

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 2.6.a | Admin user clicks **Admin** in the navbar and opens the MFA / Security admin area (e.g. `/admin/mfa`). | Admin MFA page opens with stats, enforcement policy, and user list (or equivalent). |
| [ ] | 2.6.b | Admin views the MFA statistics section. | Page shows totals (e.g. total users, MFA-enabled count) and enforcement status. |
| [ ] | 2.6.c | Admin changes the MFA enforcement policy (e.g. optional / required for admins / required for all) and saves. | Policy is updated; page reflects the new setting. |
| [ ] | 2.6.d | Admin resets MFA for a specific user (e.g. for lockout recovery). | That user’s MFA and trusted devices are cleared; admin sees confirmation or updated list. |

---

## 3.0 Ticketing

### 3.1 List and filter tickets

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 3.1.a | Logged-in user navigates to **Tickets** (e.g. via nav or `/tickets`). | Tickets page opens with a list of tickets (e.g. active only by default). |
| [ ] | 3.1.b | User uses filters (status, assignee, reporter) if the UI provides them. | List updates to show only tickets matching the selected filters. |

### 3.2 Create ticket

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 3.2.a | User clicks **Create Ticket** (or equivalent) on the Tickets page. | A form or modal appears with at least: description (required), and optionally location/table and priority. |
| [ ] | 3.2.b | User fills in the description (and any optional fields) and submits. | A success message or redirect; the new ticket appears in the list with a ticket number; current user is shown as reporter. |

### 3.3 View ticket detail

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 3.3.a | User clicks a ticket in the list or from the dashboard. | App navigates to the ticket detail page (e.g. `/tickets/:id`). |
| [ ] | 3.3.b | Ticket detail page loads. | User sees full ticket info: status, priority, reporter, assignee, description, timestamps. |

### 3.4 Assign ticket

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 3.4.a | On the ticket list or detail, user clicks **Assign to me** (or equivalent). | Ticket is assigned to the current user; UI updates to show them as assignee. |

### 3.5 Update ticket (experts and admins only)

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 3.5.a | Expert or admin opens a ticket detail and changes status (e.g. open → in progress → closed) and saves. | Status updates; if closed, ticket shows as closed and closed time (or equivalent). |
| [ ] | 3.5.b | A **non-expert** user tries to change ticket status or update the ticket (if the UI exposes that). | User cannot update the ticket; they see an error or the option is hidden/disabled (e.g. “Only experts and admins can update tickets”). |

### 3.6 Dashboard and leaderboard

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 3.6.a | User opens **Dashboard** (e.g. from nav or `/dashboard`). | Dashboard loads with active tickets (e.g. table or list) and links to open ticket details. |
| [ ] | 3.6.b | User opens **Leaderboard** (e.g. from nav or `/leaderboard`). | Leaderboard page shows experts ranked by closed-ticket count (or equivalent). |

---

## 4.0 Chat and messaging

### 4.1 Channels (list, create, join)

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 4.1.a | User navigates to **Chat** (e.g. from nav or `/chat`). | Chat layout appears: sidebar with channels and DMs, and a main message area. |
| [ ] | 4.1.b | User looks at the channel list in the sidebar. | User sees default channels (e.g. #General, #Get-Help) and any channels they have joined. |
| [ ] | 4.1.c | User clicks **Create channel** (e.g. “+” next to Channels). | A modal or form appears: channel name, description, public/private. |
| [ ] | 4.1.d | User enters a new channel name (2–80 chars, alphanumeric + dashes) and submits. | New channel is created; user is in it and the channel appears in their sidebar. |
| [ ] | 4.1.e | User uses the UI to **join** a public channel (if join is available). | User joins the channel; it appears in their sidebar and they can open it. |

### 4.2 Direct messages

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 4.2.a | User clicks **New message** or **Send a message** (or equivalent). | A modal or panel opens to search and select another participant. |
| [ ] | 4.2.b | User types in the search box to find another user. | A list of matching users appears. |
| [ ] | 4.2.c | User selects a user and confirms (e.g. “Open” or “Start conversation”). | A DM conversation opens and appears in the sidebar; user can send messages. |

### 4.3 Send and receive messages

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 4.3.a | User selects a channel or DM in the sidebar. | That conversation becomes active; message history loads in the main area. |
| [ ] | 4.3.b | User types a message in the composer and sends it. | The message appears in the conversation for the user (and for others in the same channel/DM in real time). |
| [ ] | 4.3.c | Another user (or same user in another tab) sends a message in the same channel/DM. | The new message appears in the conversation without refreshing the page. |
| [ ] | 4.3.d | User sends a very high number of messages in a short time (e.g. >50 in one minute). | App shows an error or rate-limit message (e.g. “Rate limit exceeded. Max 50 messages per minute.”). |

### 4.4 Get-Help channel and agent

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 4.4.a | User selects the **#Get-Help** channel in the sidebar. | #Get-Help opens like any channel: message list and composer. |
| [ ] | 4.4.b | User sends a message in #Get-Help. | Message appears in the channel. |
| [ ] | 4.4.c | User waits for a response (or refreshes). | An agent/system reply appears in the same channel as a new message. |

### 4.5 Cursor CLI / external agent (optional)

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 4.5.a | User (or developer) uses Cursor CLI or another client that calls the agent API with a message. | The client receives a reply from the agent (e.g. in Cursor or in the response). |

---

## 5.0 Workers and experts

### 5.1 List workers

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 5.1.a | User navigates to a page or section that lists workers (if the app exposes it). | A list of workers is shown (with optional search or role filter if available). |

### 5.2 Worker profile (e.g. Logan’s profile)

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 5.2.a | User opens **Logan’s Profile** (or Worker profile) from the app (e.g. link or `/worker-profile`). | Profile page loads. |
| [ ] | 5.2.b | Page loads and displays profile data. | User sees the worker’s profile information (e.g. name, role, details from Workday). |

### 5.3 Assign / remove expert (admin only)

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 5.3.a | Admin navigates to the place where they can assign the expert role (e.g. worker list or profile) and assigns expert to a worker. | UI confirms the worker is now an expert (e.g. badge, role label, or list update). |
| [ ] | 5.3.b | Admin removes the expert role from a worker. | UI confirms the worker is no longer an expert. |
| [ ] | 5.3.c | A **non-admin** user tries to assign or remove expert (if the UI exposes it to them). | User cannot perform the action; they see an error or the option is hidden/disabled. |

### 5.4 Sync status (if UI exposed)

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 5.4.a | Admin or support user opens the Workday sync status view (if available). | Page shows current sync status (e.g. last sync time, state). |
| [ ] | 5.4.b | Admin triggers a sync (e.g. “Sync now” or “Trigger sync”) if the UI offers it. | UI shows that sync was started or completed (e.g. success message or status update). |

---

## 6.0 Settings and Cursor CLI

### 6.1 Security settings

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 6.1.a | User opens **Settings** and goes to **Security** (e.g. `/settings/security`). | Security page shows: MFA status, Enable/Disable MFA, backup codes, trusted devices, and Cursor CLI / Workday MCP section (if applicable). |

### 6.2 Cursor CLI / Workday MCP setup

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 6.2.a | User opens Settings and finds the **Cursor CLI / Workday MCP** instructions. | User sees copyable snippet (e.g. for `.cursor/mcp.json`) and steps to configure the Workday MCP server and restart Cursor. |
| [ ] | 6.2.b | User copies the snippet, configures the MCP server, and restarts Cursor. | User can use Workday tools in Cursor (e.g. get worker profile, ticket tools). |

---

## 7.0 Admin (optional features)

*These depend on admin features being available (e.g. admin_sync, admin_config).*

### 7.1 Admin sync (Workday user sync)

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 7.1.a | Admin navigates to the **Admin** area and opens the **Sync** or **Workday sync** section. | Admin sees options to sync users (e.g. single user by Workday ID, bulk sync). |
| [ ] | 7.1.b | Admin syncs a **single user** by Workday ID (e.g. enters ID and clicks “Sync user”). | UI shows success or result (e.g. “User synced” or job completed). |
| [ ] | 7.1.c | Admin triggers a **bulk sync** (e.g. “Sync all” or “Bulk sync”). | UI confirms the job was started and may show a job ID or “In progress.” |
| [ ] | 7.1.d | Admin checks the status of a sync job (e.g. via “Check status” or job list). | UI shows the job status (e.g. pending, running, completed, failed). |
| [ ] | 7.1.e | Admin opens **Sync history** (if available). | A list of past sync runs or jobs is displayed. |

### 7.2 Admin Workday config

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 7.2.a | Admin navigates to the **Admin** dashboard and finds **Workday config** (or **Configuration**). | Admin sees the Workday configuration section (e.g. current tenant, endpoint, or connection info). |
| [ ] | 7.2.b | Admin views the current Workday config. | Current settings are displayed (read-only or in a form). |
| [ ] | 7.2.c | Admin updates one or more Workday config values and saves. | UI confirms the config was updated (e.g. success message); displayed values reflect the change. |

---

## 8.0 Workday Orchestration (CreateTicket)

*Validates that the CreateTicket orchestration tool is used correctly and that created tickets appear in the app (confirming they reached the backend / Workday business object).*

### 8.1 Create ticket via orchestration and verify in backend (Workday BO)

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 8.1.a | User creates a ticket via the app’s **Create Ticket** flow (or via Cursor/MCP using the Workday **launch_create_ticket_orchestration** tool) with required fields: reporter, description, status, priority, table number; optionally assignee. | Success response or confirmation that the ticket was created (e.g. success message, ticket ID, or orchestration response). |
| [ ] | 8.1.b | User navigates to **Tickets** (e.g. via nav or `/tickets`). | Tickets list loads; the newly created ticket appears in the list (confirming it reached the backend / Workday business object). |
| [ ] | 8.1.c | User opens the new ticket from the list (clicks to view detail). | Ticket detail page shows the same reporter, description, status, priority, table number (and assignee if provided). |
| [ ] | 8.1.d | User creates a ticket with only required fields (no assignee) via the orchestration flow. | Ticket is created successfully; it appears in the Tickets list and in detail view with assignee empty or unset. |

### 8.2 Orchestration tool configuration (Cursor / MCP)

| Verified | Step | User action | Expected result (what user sees) |
|----------|------|-------------|----------------------------------|
| [ ] | 8.2.a | User (or developer) has configured the Workday MCP server with `WORKDAY_ORCHESTRATE_BASE_URL` and uses **launch_create_ticket_orchestration** in Cursor (or another MCP client). | Tool executes without configuration error; orchestration launch response is returned. |
| [ ] | 8.2.b | After a successful orchestration launch, user opens the app’s **Tickets** page. | The ticket created by the orchestration appears in the list, confirming end-to-end flow from orchestration to Workday BO to app. |

---

## Quick reference: routes and entry points

| Area   | Where the user goes (routes / UI) |
|--------|-----------------------------------|
| Auth   | Login page, Register page (e.g. `/login`, `/register`) |
| MFA    | Settings → Security (`/settings/security`), Admin → MFA (`/admin/mfa`) |
| Tickets| Tickets list, ticket detail, Dashboard, Leaderboard (`/tickets`, `/tickets/:id`, `/dashboard`, `/leaderboard`) |
| Chat   | Chat (`/chat`); sidebar for channels and DMs |
| Other  | Dashboard, Leaderboard, Worker profile (`/dashboard`, `/leaderboard`, `/worker-profile`) |
| Admin  | Admin area (e.g. sync, Workday config, MFA management) |
| Agent  | In-app: #Get-Help channel; externally: Cursor CLI / agent API |
| Workday Orchestration | Create Ticket flow (app or Cursor/MCP **launch_create_ticket_orchestration**); verify in Tickets list/detail |

---

## Notes for test automation

- **User-only flow**: All steps are written for the end user in the UI. E2E tests should drive the browser (or client) the same way: navigate, click, type, select. Do not call backend APIs directly when validating user-facing behavior.
- **Session**: Use one browser (or session) for all steps after login (and after MFA verify when applicable).
- **Order**: Run registration (1.1) and first-time setup (e.g. default channels) before chat and Get-Help agent steps (4.x).
- **Roles**: Use separate user accounts for: regular user, expert, admin to cover ticket updates (3.5), expert assign/remove (5.3), admin MFA (2.6), and admin sync/config (7.x).
- **MFA**: If the app does not yet show an MFA step after password login, test MFA only via Settings (2.1, 2.3, 2.4) and Admin (2.6).
- **Workday Orchestration (8.0)**: To confirm tickets reach the backend (Workday BO), create a ticket via the orchestration (app or MCP tool), then open the Tickets list and ticket detail in the app; the ticket must appear with the same data.

Walk through this document step-by-step to validate the entire app flow from the user’s perspective and to add or align E2E tests for each step.
