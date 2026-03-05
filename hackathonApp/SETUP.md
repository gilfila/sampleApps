# Setup Instructions

## Prerequisites

- Python 3.11+
- Node.js 16+ and npm
- PostgreSQL database
- Workday Integration System User credentials

## Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the backend directory (copy from `backend/.env.example`). Key variables:
   - **Database:** `DATABASE_URL`, `SECRET_KEY`
   - **Workday auth:** `WORKDAY_TENANT`, `WORKDAY_CLIENT_ID`, `WORKDAY_CLIENT_SECRET`, `WORKDAY_REFRESH_TOKEN`
   - **Extend URL pattern:** `https://api.workday.com/apps/<WORKDAY_APP_NAME>/v1/<collection_name>`
   - **Extend:** `WORKDAY_EXTEND_BASE_URL` (optional, default `https://api.workday.com`), `WORKDAY_APP_NAME`
   - **Hacker data:** `WORKDAY_HACKER_COLLECTION_NAME` — collection name for the participant CBO
   - **Ticket data:** `WORKDAY_TICKET_COLLECTION_NAME` — collection name for the ticket CBO (enables ticket sync when set)
   - **Override (optional):** `WORKDAY_REST_BASE_URL` + `WORKDAY_TENANT` or `WORKDAY_TICKETS_BUSINESS_OBJECT_URL` for explicit URLs

5. Run the application:
   ```bash
   python run.py
   ```

   The application will:
   - Create database tables automatically
   - Seed default channels (#General and #Get-Help) if they do not exist
   - Start the background scheduler for Workday sync
   - Run initial sync of workers and tickets from Workday
   - Start the Flask server on port 5000

## Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create a `.env` file in the frontend directory (optional):
   ```env
   REACT_APP_API_URL=http://localhost:5000/api
   REACT_APP_SOCKET_URL=http://localhost:5000
   ```

4. Start the development server:
   ```bash
   npm start
   ```

   The frontend will start on http://localhost:3000

## First Time Setup

1. **Initial Workday Sync**: On first startup, the backend syncs workers from the Workday Extend API. URLs are built from `WORKDAY_EXTEND_BASE_URL`, `WORKDAY_APP_NAME`, and the collection names (`WORKDAY_HACKER_COLLECTION_NAME`, `WORKDAY_TICKET_COLLECTION_NAME`). Ensure these (or the legacy URL overrides) are set in `.env`.

2. **Create Admin User**: You'll need to manually create an admin user in the database or through the API. Admin users can assign expert roles.

3. **User Registration**: Users can register using their Workday email. The system validates that the email exists in the synced worker data. New users are automatically added to the default channels (#General, #Get-Help).

   **If you see "Email not found. Please contact admin."** — the email must already exist in the `workers` table (from Workday sync, admin-created workers, or the CSV invite step below). To allow specific emails to register without Workday:
   - **CSV invites**: From the backend directory, run `python seed_invites_from_csv.py path/to/invites.csv`. Use the format `email,name,role` (see `backend/invites_example.csv`). Created workers have no password until they register.
   - **Admin API**: An admin can create workers via `POST /api/workers` with `email`, `name`, and optional `role`; those users can then register.

4. **Cursor CLI (Workday MCP)**: To use Workday tools from Cursor, go to **Settings** in the app and follow the **Cursor CLI / Workday MCP** section: add the provided snippet to `.cursor/mcp.json` in your project root and restart Cursor.

## Testing the Application

1. **Register a User**: 
   - Go to http://localhost:3000/register
   - Use an email that exists in your Workday worker data
   - Complete registration

2. **Login**: 
   - Go to http://localhost:3000/login
   - Use your registered credentials

3. **Create a Ticket**: 
   - Navigate to Tickets
   - Click "Create Ticket"
   - Fill in the description and submit

4. **Assign Expert Role** (Admin only):
   - As an admin, go to Workers
   - Find a worker and assign expert role

5. **Test Real-time Chat**:
   - Navigate to Chat
   - Join a room or start a direct message

## Deployment to Render

1. Push your code to a Git repository

2. In Render dashboard:
   - Create a new Web Service
   - Connect your repository
   - Use the `render.yaml` configuration
   - Set all environment variables
   - Deploy

3. The application will automatically:
   - Install dependencies
   - Create database tables
   - Start background sync jobs
   - Serve the application

## Troubleshooting

### Workday Sync Issues
- Verify your Workday OAuth credentials (`WORKDAY_TENANT`, `WORKDAY_CLIENT_ID`, `WORKDAY_CLIENT_SECRET`, `WORKDAY_REFRESH_TOKEN`)
- **Extend URL:** Use `WORKDAY_EXTEND_BASE_URL` (default `https://api.workday.com`), `WORKDAY_APP_NAME`, and the collection names: `WORKDAY_HACKER_COLLECTION_NAME` (participants), `WORKDAY_TICKET_COLLECTION_NAME` (tickets). Or set the legacy overrides `WORKDAY_REST_BASE_URL`/`WORKDAY_TENANT` or `WORKDAY_TICKETS_BUSINESS_OBJECT_URL`.
- Review logs for API errors and ensure your Integration System User has access to both Extend CBOs

### Database Issues
- Verify DATABASE_URL is correct
- Ensure PostgreSQL is running
- Check database user permissions

### Frontend Connection Issues
- Verify REACT_APP_API_URL points to correct backend URL
- Check CORS settings in backend
- Ensure backend is running
