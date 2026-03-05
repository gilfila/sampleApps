# Workstream 3: Security Hardening & MFA Implementation

## Design Document

**Author:** Security Engineer
**Date:** 2026-02-13
**Status:** Draft
**Scope:** Address all critical/high security issues + implement TOTP-based MFA
**Target Scale:** 1,000 users at hackathon event

---

## Table of Contents

1. [Current State Security Assessment](#1-current-state-security-assessment)
2. [Security Remediation Checklist](#2-security-remediation-checklist)
3. [MFA System Architecture](#3-mfa-system-architecture)
4. [Database Schema for MFA](#4-database-schema-for-mfa)
5. [API Endpoint Specifications](#5-api-endpoint-specifications)
6. [UI/UX Flow Diagrams](#6-uiux-flow-diagrams)
7. [Implementation Plan](#7-implementation-plan)
8. [Test Cases](#8-test-cases)
9. [OWASP Compliance Validation](#9-owasp-compliance-validation)
10. [Risks & Mitigations](#10-risks--mitigations)

---

## 1. Current State Security Assessment

### Vulnerabilities Identified

| # | Severity | Issue | File:Line | Description |
|---|----------|-------|-----------|-------------|
| V1 | **CRITICAL** | No rate limiting | `backend/app/routes/auth.py:41-73` | Login endpoint has zero rate limiting. An attacker can brute-force passwords with unlimited attempts per second. No rate limiting on any API endpoint or WebSocket handler. |
| V2 | **CRITICAL** | Weak session management | `backend/app/__init__.py:10,27` | SocketIO `cors_allowed_origins="*"` set at both initialization (line 10) and in `socketio.init_app()` (line 27). Flask-Login `remember=True` always set (auth.py:63) with 24-hour session lifetime but no refresh token mechanism. No session revocation capability. |
| V3 | **CRITICAL** | Race condition in ticket numbering | `backend/app/routes/tickets.py:76-77` | `last_ticket = Ticket.query.order_by(Ticket.ticket_number.desc()).first()` followed by `ticket_number = (last_ticket.ticket_number + 1)` is a classic TOCTOU race. Two concurrent requests can read the same max ticket_number and both try to insert with the same next number, causing either a duplicate or a unique constraint violation. |
| V4 | **HIGH** | CORS wildcard on SocketIO | `backend/app/__init__.py:10,27` | `cors_allowed_origins="*"` allows any website to establish WebSocket connections to the backend. While HTTP CORS is restricted to localhost:3000 (line 29), the WebSocket channel is wide open. |
| V5 | **HIGH** | No input sanitization | `backend/app/routes/tickets.py:71`, `backend/app/socketio_handlers.py:62` | Ticket `description` and chat `content` are stored and returned as-is. No HTML escaping or sanitization. XSS payloads stored in the database will be rendered by the React frontend via `dangerouslySetInnerHTML` or similar patterns. |
| V6 | **HIGH** | SQL injection via search | `backend/app/routes/workers.py:28-31` | `Worker.name.ilike(f'%{search}%')` uses f-string interpolation for the LIKE pattern. While SQLAlchemy parameterizes the query, the `%` wildcards are string-interpolated into the pattern, which could allow LIKE-injection (e.g., `%` to dump all results). This is low-risk with SQLAlchemy ORM but should still use proper parameterization. |
| V7 | **HIGH** | Debug mode not guarded | `backend/config.py:38` | `DevelopmentConfig` has `DEBUG = True`. The `FLASK_ENV` defaults to `'development'` in `__init__.py:18`, meaning if the environment variable is not set, the app runs in debug mode in production. Debug mode exposes stack traces, the Werkzeug debugger (RCE risk), and enables `SQLALCHEMY_RECORD_QUERIES`. |
| V8 | **MEDIUM** | Hardcoded fallback secret | `backend/config.py:7` | `SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'` -- if `SECRET_KEY` env var is not set, the fallback is a known static string. Anyone who reads this source code can forge session cookies. |
| V9 | **MEDIUM** | No password strength validation | `backend/app/routes/auth.py:19` | Registration only checks `if not email or not password`. No minimum length, complexity, or breach-list checks. |
| V10 | **LOW** | No CSRF protection | `backend/app/__init__.py` | No Flask-WTF or CSRF token middleware. Relies on SameSite=Lax cookie attribute, which is not sufficient for all attack vectors (e.g., top-level navigations via GET). |
| V11 | **LOW** | No security headers | `backend/app/__init__.py` | No `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security` headers. |

### Architecture Summary

```
Frontend (React)                    Backend (Flask)                Database (PostgreSQL)
+-----------------+                +---------------------+        +------------------+
| Login.js        | --HTTP/WS----> | auth.py (no limits) | -----> | workers table    |
| api.js (axios)  |   cookies      | tickets.py (race)   |        | tickets table    |
| socket.js       |   CORS:*       | messages.py         |        | chat_messages    |
|                 |                | socketio_handlers   |        |                  |
+-----------------+                +---------------------+        +------------------+
     No MFA                         No rate limiting                No sequences
     No TOTP UI                     Wildcard CORS on WS             No MFA tables
                                    Debug mode default
```

---

## 2. Security Remediation Checklist

### CRITICAL Priority

#### 2.1 Implement Rate Limiting

**Files to modify:**
- `backend/requirements.txt` -- add `Flask-Limiter==3.5.1`
- `backend/app/__init__.py` -- initialize limiter extension
- `backend/app/routes/auth.py` -- apply login/register rate limits
- `backend/app/routes/tickets.py` -- apply API rate limits
- `backend/app/routes/messages.py` -- apply API rate limits
- `backend/app/routes/workers.py` -- apply API rate limits
- `backend/app/socketio_handlers.py` -- apply WebSocket rate limits

**Rate limit tiers:**

| Endpoint Category | Limit | Window | Key |
|-------------------|-------|--------|-----|
| POST /api/auth/login | 5 requests | per minute | per IP |
| POST /api/auth/register | 3 requests | per minute | per IP |
| POST /api/auth/mfa/* | 5 requests | per minute | per IP + user |
| GET /api/* (authenticated) | 100 requests | per hour | per user |
| POST /api/tickets | 20 requests | per hour | per user |
| WebSocket send_message | 50 messages | per minute | per user |
| WebSocket connect | 5 connections | per minute | per IP |

**Implementation:**

```python
# backend/app/__init__.py - Add to create_app()
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per hour"],
    storage_uri="memory://",  # Use Redis in production: "redis://localhost:6379"
)

def create_app(config_name=None):
    app = Flask(__name__)
    # ... existing config ...
    limiter.init_app(app)
    # ...
```

```python
# backend/app/routes/auth.py - Apply specific limits
from app import limiter

@bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    # ... existing logic ...
    # On failure, log the attempt for monitoring
    pass

@bp.route('/register', methods=['POST'])
@limiter.limit("3 per minute")
def register():
    # ... existing logic ...
    pass
```

```python
# backend/app/socketio_handlers.py - WebSocket rate limiting
from collections import defaultdict
from time import time

# In-memory rate tracking (per-user message rates)
_ws_rate_tracker = defaultdict(list)
WS_MSG_LIMIT = 50
WS_MSG_WINDOW = 60  # seconds

def check_ws_rate_limit(user_id):
    """Check if user has exceeded WebSocket message rate limit."""
    now = time()
    # Purge old entries
    _ws_rate_tracker[user_id] = [
        t for t in _ws_rate_tracker[user_id] if now - t < WS_MSG_WINDOW
    ]
    if len(_ws_rate_tracker[user_id]) >= WS_MSG_LIMIT:
        return False  # Rate limited
    _ws_rate_tracker[user_id].append(now)
    return True

@socketio.on('send_message')
def handle_send_message(data):
    if not current_user.is_authenticated:
        emit('error', {'message': 'Not authenticated'})
        return False

    if not check_ws_rate_limit(current_user.id):
        emit('error', {'message': 'Rate limit exceeded. Max 50 messages per minute.'})
        return False
    # ... rest of handler ...
```

**429 Response format:**
```json
{
  "error": "Rate limit exceeded",
  "retry_after": 42
}
```

#### 2.2 Fix Session Management

**Files to modify:**
- `backend/config.py` -- tighten session config
- `backend/app/__init__.py` -- add session lifecycle hooks
- `backend/app/routes/auth.py` -- add session refresh endpoint

**Changes to `backend/config.py`:**

```python
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')  # Remove fallback entirely

    # Session configuration - tightened
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)   # Reduced from 24h
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = 'hackathon_session'         # Custom cookie name
    REMEMBER_COOKIE_DURATION = timedelta(hours=8)     # Match session lifetime
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = True

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("DATABASE_URL environment variable must be set in production")
    # Enforce SECRET_KEY in production
    if not Config.SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable must be set in production")
```

**Add session refresh endpoint to `backend/app/routes/auth.py`:**

```python
@bp.route('/refresh', methods=['POST'])
@login_required
def refresh_session():
    """Refresh the current session to extend expiration."""
    from flask import session
    session.modified = True  # Force session cookie refresh
    return jsonify({
        'message': 'Session refreshed',
        'user': {
            'id': current_user.id,
            'email': current_user.email,
            'name': current_user.name,
            'role': current_user.role.value
        }
    }), 200
```

**Add frontend session refresh to `frontend/src/services/auth.js`:**

```javascript
// Auto-refresh session every 30 minutes
useEffect(() => {
  if (!user) return;
  const interval = setInterval(async () => {
    try {
      await api.post('/auth/refresh');
    } catch (error) {
      // Session expired, force re-login
      setUser(null);
    }
  }, 30 * 60 * 1000); // 30 minutes
  return () => clearInterval(interval);
}, [user]);
```

#### 2.3 Fix Race Conditions in Ticket Numbering

**Files to modify:**
- `backend/app/routes/tickets.py:65-94` -- replace application-level sequencing
- New migration file -- create PostgreSQL sequence

**Option A: PostgreSQL Sequence (Recommended)**

Create a migration:
```sql
-- migrations/003_ticket_sequence.sql
CREATE SEQUENCE IF NOT EXISTS ticket_number_seq START WITH 1 INCREMENT BY 1;

-- Seed the sequence to the current max ticket_number
SELECT setval('ticket_number_seq', COALESCE((SELECT MAX(ticket_number) FROM tickets), 0));
```

Modify `backend/app/routes/tickets.py`:

```python
@bp.route('', methods=['POST'])
@login_required
def create_ticket():
    data = request.get_json()

    description = data.get('description')
    if not description:
        return jsonify({'error': 'Description is required'}), 400

    location_table = data.get('location_table') or current_user.table

    # Use PostgreSQL sequence for atomic ticket numbering
    # This is safe under concurrent access -- each call gets a unique number
    result = db.session.execute(db.text("SELECT nextval('ticket_number_seq')"))
    ticket_number = result.scalar()

    ticket = Ticket(
        ticket_number=ticket_number,
        reporter_id=current_user.id,
        description=description,
        location_table=location_table,
        status=TicketStatus.OPEN,
        priority=TicketPriority(data.get('priority', 'normal')),
        ticket_opened=datetime.utcnow(),
        sync_status=SyncStatus.PENDING
    )

    db.session.add(ticket)
    db.session.commit()

    ticket_service.queue_workday_sync(ticket.id)
    return jsonify(ticket_to_dict(ticket)), 201
```

**Option B: SELECT ... FOR UPDATE (Alternative)**

```python
# Within a transaction with row-level locking
with db.session.begin_nested():
    last_ticket = Ticket.query.order_by(
        Ticket.ticket_number.desc()
    ).with_for_update().first()
    ticket_number = (last_ticket.ticket_number + 1) if last_ticket else 1
    # ... create ticket ...
```

**Recommendation:** Option A (PostgreSQL sequence) is strongly preferred. It is lock-free, has no contention, and is the idiomatic PostgreSQL solution for auto-incrementing business identifiers.

### HIGH Priority

#### 2.4 Lock Down CORS

**Files to modify:**
- `backend/app/__init__.py:10,27,29` -- fix SocketIO and HTTP CORS
- `backend/config.py` -- make origins configurable

**Changes:**

```python
# backend/config.py - Add CORS config
class Config:
    # CORS
    CORS_ORIGINS = os.environ.get(
        'CORS_ORIGINS', 'http://localhost:3000'
    ).split(',')

class ProductionConfig(Config):
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',')
    if not CORS_ORIGINS or CORS_ORIGINS == ['']:
        raise ValueError("CORS_ORIGINS must be set in production")
```

```python
# backend/app/__init__.py
# BEFORE (vulnerable):
socketio = SocketIO(cors_allowed_origins="*")
# ...
socketio.init_app(app, cors_allowed_origins="*")
CORS(app, supports_credentials=True, origins=["http://localhost:3000", "http://127.0.0.1:3000"])

# AFTER (hardened):
socketio = SocketIO()  # No cors here; set during init_app
# ...
def create_app(config_name=None):
    # ...
    allowed_origins = app.config['CORS_ORIGINS']
    socketio.init_app(app, cors_allowed_origins=allowed_origins)
    CORS(app, supports_credentials=True, origins=allowed_origins)
```

#### 2.5 Input Sanitization

**Files to modify:**
- `backend/app/utils/sanitize.py` -- new utility module
- `backend/app/routes/tickets.py:71` -- sanitize ticket description
- `backend/app/routes/messages.py:66-68` -- sanitize message content
- `backend/app/socketio_handlers.py:62` -- sanitize WebSocket message content
- `backend/requirements.txt` -- add `bleach==6.1.0`

**Implementation:**

```python
# backend/app/utils/sanitize.py
import bleach

# Allowed tags for rich text (if needed -- empty for plain text)
ALLOWED_TAGS = []        # No HTML tags allowed
ALLOWED_ATTRIBUTES = {}  # No attributes allowed

def sanitize_input(text, max_length=10000):
    """Sanitize user input: strip HTML tags, enforce length limit."""
    if text is None:
        return None
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    # Strip all HTML
    clean = bleach.clean(text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)
    # Enforce length
    return clean[:max_length]

def sanitize_search(text, max_length=200):
    """Sanitize search input: strip HTML, escape LIKE wildcards."""
    if text is None:
        return None
    clean = bleach.clean(text, tags=[], attributes={}, strip=True)
    # Escape LIKE metacharacters
    clean = clean.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    return clean[:max_length]
```

**Apply in routes:**

```python
# backend/app/routes/tickets.py
from app.utils.sanitize import sanitize_input

@bp.route('', methods=['POST'])
@login_required
def create_ticket():
    data = request.get_json()
    description = sanitize_input(data.get('description'), max_length=5000)
    if not description:
        return jsonify({'error': 'Description is required'}), 400
    # ...
```

```python
# backend/app/routes/workers.py
from app.utils.sanitize import sanitize_search

@bp.route('', methods=['GET'])
@login_required
def get_workers():
    search = request.args.get('search')
    if search:
        search = sanitize_search(search)
        query = query.filter(
            (Worker.name.ilike(f'%{search}%', escape='\\')) |
            (Worker.email.ilike(f'%{search}%', escape='\\'))
        )
```

#### 2.6 Remove Debug Mode from Production

**Files to modify:**
- `backend/app/__init__.py:18` -- change default to production
- `backend/config.py:38` -- keep dev config but ensure it is never the default

```python
# backend/app/__init__.py - Change default environment
config_name = config_name or os.getenv('FLASK_ENV', 'production')  # Default to production
```

#### 2.7 Add Security Headers

**Files to modify:**
- `backend/app/__init__.py` -- add after_request handler

```python
# backend/app/__init__.py - Inside create_app()
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '0'  # Disabled in favor of CSP
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self' ws://localhost:5000 wss://localhost:5000; "
        "frame-ancestors 'none';"
    )
    if not app.debug:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
```

### MEDIUM Priority

#### 2.8 Rotate Hardcoded Secrets

**Files to modify:**
- `backend/config.py:7` -- remove fallback secret

```python
# BEFORE:
SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

# AFTER:
SECRET_KEY = os.environ.get('SECRET_KEY')

class DevelopmentConfig(Config):
    SECRET_KEY = Config.SECRET_KEY or 'dev-only-secret-not-for-production'
    # ... rest of dev config ...
```

#### 2.9 Add Password Strength Validation

**Files to modify:**
- `backend/app/utils/auth.py` -- add password validation function
- `backend/app/routes/auth.py` -- call validation on registration

```python
# backend/app/utils/auth.py
import re

def validate_password(password):
    """Validate password strength. Returns (is_valid, error_message)."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if len(password) > 128:
        return False, "Password must be at most 128 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one digit"
    return True, None
```

---

## 3. MFA System Architecture

### 3.1 Enrollment Flow

```
User                     Frontend                    Backend                     DB
 |                          |                           |                         |
 |  Click "Enable MFA"     |                           |                         |
 |------------------------->|                           |                         |
 |                          |  POST /api/auth/mfa/enroll|                         |
 |                          |-------------------------->|                         |
 |                          |                           |  Generate TOTP secret   |
 |                          |                           |  Store (disabled)       |
 |                          |                           |------------------------>|
 |                          |  {qr_code, manual_key}    |                         |
 |                          |<--------------------------|                         |
 |  Display QR code         |                           |                         |
 |<-------------------------|                           |                         |
 |                          |                           |                         |
 |  Scan QR + Enter code    |                           |                         |
 |------------------------->|                           |                         |
 |                          |  POST /mfa/verify-enrollment                        |
 |                          |  {totp_code: "123456"}    |                         |
 |                          |-------------------------->|                         |
 |                          |                           |  Validate TOTP code     |
 |                          |                           |  Enable MFA             |
 |                          |                           |  Generate backup codes  |
 |                          |                           |------------------------>|
 |                          |  {backup_codes: [...]}    |                         |
 |                          |<--------------------------|                         |
 |  Display backup codes    |                           |                         |
 |  (one-time view)         |                           |                         |
 |<-------------------------|                           |                         |
```

**Key design decisions:**
- MFA enrollment is opt-in by default, with admin toggle to enforce for all users
- TOTP secret is generated server-side using `pyotp` library
- Secret is stored encrypted in the database (AES-256-GCM via `cryptography` library)
- QR code is generated server-side as a base64 PNG using `qrcode` library
- Backup codes are generated as 8 random 8-character alphanumeric strings
- Backup codes are stored as bcrypt hashes (same as passwords)
- Enrollment is not complete until the user verifies a TOTP code

### 3.2 Login Flow (with MFA)

```
User                     Frontend                    Backend                     DB
 |                          |                           |                         |
 |  Enter email + password  |                           |                         |
 |------------------------->|                           |                         |
 |                          |  POST /api/auth/login     |                         |
 |                          |  {email, password}        |                         |
 |                          |-------------------------->|                         |
 |                          |                           |  Verify credentials     |
 |                          |                           |  Check MFA enabled?     |
 |                          |                           |------------------------>|
 |                          |                           |                         |
 |                          |         [MFA NOT enabled] |                         |
 |                          |  {user: {...}}  (200)     |                         |
 |                          |<--------------------------|                         |
 |                          |                           |                         |
 |                          |         [MFA IS enabled]  |                         |
 |                          |  {mfa_required: true,     |                         |
 |                          |   mfa_token: "temp..."}   |                         |
 |                          |  (200, partial auth)      |                         |
 |                          |<--------------------------|                         |
 |  Show TOTP input screen  |                           |                         |
 |<-------------------------|                           |                         |
 |                          |                           |                         |
 |  Enter TOTP code         |                           |                         |
 |  [x] Remember device     |                           |                         |
 |------------------------->|                           |                         |
 |                          |  POST /mfa/verify-login   |                         |
 |                          |  {mfa_token, totp_code,   |                         |
 |                          |   remember_device: true}  |                         |
 |                          |-------------------------->|                         |
 |                          |                           |  Validate TOTP          |
 |                          |                           |  Create full session    |
 |                          |                           |  (If remember: create   |
 |                          |                           |   trusted device token) |
 |                          |                           |------------------------>|
 |                          |  {user: {...}}  (200)     |                         |
 |                          |  Set-Cookie: device_token |                         |
 |                          |<--------------------------|                         |
 |  Redirect to dashboard   |                           |                         |
 |<-------------------------|                           |                         |
```

**MFA token design:**
- After successful password verification, backend issues a short-lived (5 minute) JWT-like `mfa_token` signed with the app's SECRET_KEY
- The `mfa_token` payload contains `{user_id, exp, purpose: "mfa_verify"}`
- The user is NOT logged in at this stage -- Flask-Login session is NOT created
- The `mfa_token` is returned in the response body (not a cookie) and must be sent back with the TOTP verification request
- This prevents a user who knows the password but not the TOTP code from accessing any authenticated endpoints

**Trusted device flow:**
- If user checks "Remember this device", a `device_token` cookie is set (HttpOnly, Secure, 30-day expiry)
- The token is a random 64-character hex string stored in the `trusted_devices` table
- On subsequent logins from the same device, if the `device_token` cookie is present and valid, MFA is skipped
- Trusted devices expire after 30 days and can be revoked by the user or admin

### 3.3 Recovery Flow

```
User                     Frontend                    Backend                     DB
 |                          |                           |                         |
 |  On MFA verify screen    |                           |                         |
 |  Click "Use backup code" |                           |                         |
 |------------------------->|                           |                         |
 |                          |  POST /mfa/verify-login   |                         |
 |                          |  {mfa_token,              |                         |
 |                          |   backup_code: "ABCD1234"}|                         |
 |                          |-------------------------->|                         |
 |                          |                           |  Hash input, compare    |
 |                          |                           |  to stored hashes       |
 |                          |                           |  Mark code as used      |
 |                          |                           |------------------------>|
 |                          |  {user: {...},            |                         |
 |                          |   backup_codes_remaining: 5}                        |
 |                          |<--------------------------|                         |
 |  Show warning if low     |                           |                         |
 |<-------------------------|                           |                         |
```

**Admin reset flow:**
```
Admin                    Frontend                    Backend                     DB
 |                          |                           |                         |
 |  Admin panel: Reset      |                           |                         |
 |  MFA for user X          |                           |                         |
 |------------------------->|                           |                         |
 |                          |  POST /admin/mfa/reset/X  |                         |
 |                          |-------------------------->|                         |
 |                          |                           |  Verify admin role      |
 |                          |                           |  Delete user_mfa row    |
 |                          |                           |  Delete trusted_devices |
 |                          |                           |  Log admin action       |
 |                          |                           |------------------------>|
 |                          |  {message: "MFA reset"}   |                         |
 |                          |<--------------------------|                         |
 |  Confirm to admin        |                           |                         |
 |<-------------------------|                           |                         |
```

### 3.4 Integration Points with Existing Auth System

```
backend/app/routes/auth.py
  login()          -- MODIFY: Add MFA check after password verification
  register()       -- NO CHANGE: MFA is enrolled separately
  logout()         -- MODIFY: Clear trusted device cookie if present
  get_current_user -- NO CHANGE
  + refresh()      -- NEW: Session refresh (from Section 2.2)

backend/app/routes/mfa.py   -- NEW BLUEPRINT
  enroll()
  verify_enrollment()
  verify_login()
  generate_backup_codes()
  disable()

backend/app/routes/admin.py  -- NEW OR EXTEND workers.py
  reset_user_mfa()
  get_mfa_status()
  enforce_mfa_toggle()

backend/app/utils/mfa.py     -- NEW MODULE
  generate_totp_secret()
  generate_qr_code()
  verify_totp_code()
  generate_backup_codes()
  hash_backup_code()
  verify_backup_code()
  encrypt_secret() / decrypt_secret()
  generate_mfa_token() / verify_mfa_token()
  generate_device_token()
```

---

## 4. Database Schema for MFA

### 4.1 Migration SQL

```sql
-- migrations/004_mfa_tables.sql

-- Table for user MFA configuration
CREATE TABLE user_mfa (
    user_id INTEGER PRIMARY KEY REFERENCES workers(id) ON DELETE CASCADE,
    totp_secret_encrypted BYTEA NOT NULL,          -- AES-256-GCM encrypted TOTP secret
    totp_secret_nonce BYTEA NOT NULL,              -- Nonce used for encryption
    is_enabled BOOLEAN NOT NULL DEFAULT FALSE,      -- MFA enabled after verification
    backup_codes JSONB NOT NULL DEFAULT '[]'::jsonb, -- Array of bcrypt-hashed backup codes
    backup_codes_remaining INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Table for trusted (remembered) devices
CREATE TABLE trusted_devices (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    device_token_hash VARCHAR(128) NOT NULL,       -- SHA-256 hash of the device token
    user_agent VARCHAR(500),                        -- Browser user-agent for display
    ip_address VARCHAR(45),                         -- IP at time of trust
    last_used_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_trusted_devices_user ON trusted_devices(user_id);
CREATE INDEX idx_trusted_devices_token ON trusted_devices(device_token_hash);
CREATE INDEX idx_trusted_devices_expires ON trusted_devices(expires_at);

-- Table for MFA audit log
CREATE TABLE mfa_audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,                    -- 'enrolled', 'login_success', 'login_failed',
                                                    -- 'backup_code_used', 'disabled', 'admin_reset'
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    details JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mfa_audit_user ON mfa_audit_log(user_id);
CREATE INDEX idx_mfa_audit_action ON mfa_audit_log(action);
CREATE INDEX idx_mfa_audit_created ON mfa_audit_log(created_at);

-- App-wide MFA enforcement setting
CREATE TABLE app_settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by INTEGER REFERENCES workers(id)
);

INSERT INTO app_settings (key, value) VALUES ('mfa_enforcement', '"optional"'::jsonb);
-- Possible values: "optional", "required_for_admins", "required_for_all"
```

### 4.2 SQLAlchemy Models

```python
# backend/app/models.py - Add to existing models

class UserMFA(db.Model):
    """MFA configuration for a user"""
    __tablename__ = 'user_mfa'

    user_id = db.Column(db.Integer, db.ForeignKey('workers.id', ondelete='CASCADE'), primary_key=True)
    totp_secret_encrypted = db.Column(db.LargeBinary, nullable=False)
    totp_secret_nonce = db.Column(db.LargeBinary, nullable=False)
    is_enabled = db.Column(db.Boolean, nullable=False, default=False)
    backup_codes = db.Column(db.JSON, nullable=False, default=list)
    backup_codes_remaining = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('Worker', backref=db.backref('mfa', uselist=False))


class TrustedDevice(db.Model):
    """Trusted device for MFA remember-me"""
    __tablename__ = 'trusted_devices'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('workers.id', ondelete='CASCADE'), nullable=False)
    device_token_hash = db.Column(db.String(128), nullable=False)
    user_agent = db.Column(db.String(500))
    ip_address = db.Column(db.String(45))
    last_used_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('Worker', backref='trusted_devices')


class MFAAuditLog(db.Model):
    """Audit log for MFA events"""
    __tablename__ = 'mfa_audit_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('workers.id', ondelete='CASCADE'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class AppSetting(db.Model):
    """Application-wide settings"""
    __tablename__ = 'app_settings'

    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.JSON, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=True)
```

---

## 5. API Endpoint Specifications

### 5.1 MFA Enrollment

#### POST /api/auth/mfa/enroll

Start MFA enrollment. Generates a TOTP secret and returns a QR code.

**Request:**
```
POST /api/auth/mfa/enroll
Authorization: Session cookie (must be authenticated)
Content-Type: application/json

{}
```

**Response (200 OK):**
```json
{
  "qr_code": "data:image/png;base64,iVBORw0KGgo...",
  "manual_key": "JBSWY3DPEHPK3PXP",
  "issuer": "HackathonApp",
  "account": "user@example.com"
}
```

**Error Responses:**
- `400`: MFA already enabled for this user
- `401`: Not authenticated
- `429`: Rate limited

---

#### POST /api/auth/mfa/verify-enrollment

Verify the TOTP code to complete MFA enrollment.

**Request:**
```json
{
  "totp_code": "123456"
}
```

**Response (200 OK):**
```json
{
  "message": "MFA enabled successfully",
  "backup_codes": [
    "ABCD1234",
    "EFGH5678",
    "IJKL9012",
    "MNOP3456",
    "QRST7890",
    "UVWX1234",
    "YZAB5678",
    "CDEF9012"
  ],
  "backup_codes_count": 8,
  "warning": "Save these backup codes securely. They will not be shown again."
}
```

**Error Responses:**
- `400`: Invalid TOTP code, or no pending enrollment
- `401`: Not authenticated
- `429`: Rate limited (5 attempts per minute)

---

### 5.2 MFA Login Verification

#### POST /api/auth/mfa/verify-login

Verify TOTP code during login (after password is verified).

**Request:**
```json
{
  "mfa_token": "eyJ...",
  "totp_code": "123456",
  "remember_device": true
}
```

**Alternative with backup code:**
```json
{
  "mfa_token": "eyJ...",
  "backup_code": "ABCD1234",
  "remember_device": false
}
```

**Response (200 OK):**
```json
{
  "message": "Login successful",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe",
    "role": "hacker"
  },
  "backup_codes_remaining": 7
}
```

If `remember_device: true`, a `Set-Cookie: device_token=<hex>; HttpOnly; Secure; SameSite=Lax; Max-Age=2592000` header is included.

**Error Responses:**
- `400`: Invalid or expired TOTP code
- `401`: Invalid or expired mfa_token
- `429`: Rate limited (5 attempts per minute)

---

### 5.3 Backup Codes

#### POST /api/auth/mfa/backup-codes

Regenerate backup codes. Invalidates all existing backup codes.

**Request:**
```json
{
  "password": "current_password"
}
```

**Response (200 OK):**
```json
{
  "backup_codes": ["ABCD1234", "EFGH5678", "..."],
  "backup_codes_count": 8,
  "warning": "Previous backup codes have been invalidated."
}
```

---

### 5.4 Disable MFA

#### DELETE /api/auth/mfa/disable

Disable MFA for the current user.

**Request:**
```json
{
  "password": "current_password",
  "totp_code": "123456"
}
```

**Response (200 OK):**
```json
{
  "message": "MFA disabled successfully"
}
```

---

### 5.5 Admin Endpoints

#### POST /api/admin/mfa/reset/:user_id

Admin resets a user's MFA (for lockout recovery).

**Request:**
```
POST /api/admin/mfa/reset/42
Authorization: Session cookie (must be admin)
```

**Response (200 OK):**
```json
{
  "message": "MFA reset for user 42",
  "user_email": "locked.out@example.com"
}
```

---

#### GET /api/admin/mfa/status

View MFA enrollment statistics.

**Response (200 OK):**
```json
{
  "total_users": 1000,
  "mfa_enabled": 450,
  "mfa_disabled": 550,
  "enforcement": "optional",
  "recent_lockouts": 3,
  "trusted_devices": 320
}
```

---

#### PUT /api/admin/mfa/enforcement

Toggle MFA enforcement policy.

**Request:**
```json
{
  "policy": "required_for_all"
}
```

Valid values: `"optional"`, `"required_for_admins"`, `"required_for_all"`

**Response (200 OK):**
```json
{
  "message": "MFA enforcement updated",
  "policy": "required_for_all"
}
```

---

### 5.6 Modified Login Endpoint

#### POST /api/auth/login (Modified)

**New response when MFA is required:**
```json
{
  "mfa_required": true,
  "mfa_token": "eyJhbGciOiJIUzI1NiIs...",
  "mfa_token_expires": 300
}
```

The existing `{message: "Login successful", user: {...}}` response is returned only when MFA is not enabled for the user, OR when the request includes a valid `device_token` cookie for a trusted device.

---

## 6. UI/UX Flow Diagrams

### 6.1 MFA Enrollment Page

```
+---------------------------------------------+
|  Account Security Settings                   |
+---------------------------------------------+
|                                              |
|  Two-Factor Authentication                   |
|  [Status: Not Enabled]                       |
|                                              |
|  Add an extra layer of security to your      |
|  account by requiring a verification code    |
|  from your authenticator app.                |
|                                              |
|  [Enable Two-Factor Authentication]          |
|                                              |
+---------------------------------------------+

         |  Click "Enable"
         v

+---------------------------------------------+
|  Set Up Two-Factor Authentication            |
+---------------------------------------------+
|                                              |
|  Step 1: Scan QR Code                        |
|                                              |
|  Open your authenticator app (Google         |
|  Authenticator, Authy, etc.) and scan this   |
|  QR code:                                    |
|                                              |
|  +-------------------+                       |
|  |  [QR CODE IMAGE]  |                       |
|  +-------------------+                       |
|                                              |
|  Can't scan? Enter this key manually:        |
|  [JBSWY3DPEHPK3PXP] [Copy]                  |
|                                              |
|  Step 2: Verify Code                         |
|                                              |
|  Enter the 6-digit code from your app:       |
|  [ _ _ _ _ _ _ ]                             |
|                                              |
|  [Cancel]  [Verify and Enable]               |
|                                              |
+---------------------------------------------+

         |  Verify code
         v

+---------------------------------------------+
|  Save Your Backup Codes                      |
+---------------------------------------------+
|                                              |
|  [!] IMPORTANT: Save these backup codes      |
|  in a safe place. If you lose access to      |
|  your authenticator app, you can use these    |
|  codes to sign in.                           |
|                                              |
|  Each code can only be used once.            |
|                                              |
|  +-----------------------------------+       |
|  |  ABCD-1234    EFGH-5678           |       |
|  |  IJKL-9012    MNOP-3456           |       |
|  |  QRST-7890    UVWX-1234           |       |
|  |  YZAB-5678    CDEF-9012           |       |
|  +-----------------------------------+       |
|                                              |
|  [Download as Text] [Copy to Clipboard]      |
|                                              |
|  [ ] I have saved my backup codes            |
|                                              |
|  [Done]  (disabled until checkbox is checked)|
|                                              |
+---------------------------------------------+
```

### 6.2 Login with MFA

```
+---------------------------------------------+
|  Login                                       |
+---------------------------------------------+
|                                              |
|  Email:    [user@example.com              ]  |
|  Password: [*************************    ]  |
|                                              |
|  [Login]                                     |
|                                              |
+---------------------------------------------+

         |  Password verified, MFA required
         v

+---------------------------------------------+
|  Two-Factor Verification                     |
+---------------------------------------------+
|                                              |
|  Enter the 6-digit code from your            |
|  authenticator app:                          |
|                                              |
|  [ _ _ _ _ _ _ ]                             |
|                                              |
|  [x] Remember this device for 30 days       |
|                                              |
|  [Verify]                                    |
|                                              |
|  ---                                         |
|  Lost your authenticator?                    |
|  [Use a backup code instead]                 |
|                                              |
+---------------------------------------------+

         |  If "Use backup code" clicked
         v

+---------------------------------------------+
|  Enter Backup Code                           |
+---------------------------------------------+
|                                              |
|  Enter one of your backup codes:             |
|                                              |
|  [________________]                          |
|                                              |
|  [Back to authenticator code]                |
|                                              |
|  [Verify]                                    |
|                                              |
+---------------------------------------------+
```

### 6.3 Admin MFA Management Page

```
+---------------------------------------------+
|  Admin > MFA Management                      |
+---------------------------------------------+
|                                              |
|  MFA Enforcement Policy:                     |
|  ( ) Optional                                |
|  ( ) Required for Admins & Experts           |
|  (*) Required for All Users                  |
|  [Save Policy]                               |
|                                              |
+---------------------------------------------+
|  MFA Statistics                              |
|  Enrolled: 450/1000 (45%)                    |
|  [=========>                      ] 45%      |
|  Trusted Devices: 320                        |
|  Failed MFA attempts (24h): 12               |
+---------------------------------------------+
|  User MFA Status                             |
|  Search: [____________]                      |
|                                              |
|  Name           Email              MFA   Act |
|  -----------    ----------------   ---   --- |
|  John Doe       john@ex.com        Yes   [Reset] |
|  Jane Smith     jane@ex.com        No    --  |
|  Bob Wilson     bob@ex.com         Yes   [Reset] |
|  Alice Brown    alice@ex.com       Yes   [Reset] |
|                                              |
|  Showing 1-20 of 1000    [< 1 2 3 ... 50 >] |
+---------------------------------------------+
```

### 6.4 Frontend Component Structure

```
frontend/src/components/
  Auth/
    Login.js              -- MODIFY: Add MFA verification step
    MFAVerify.js          -- NEW: TOTP input after password
    BackupCodeInput.js    -- NEW: Backup code input alternative
  Settings/
    SecuritySettings.js   -- NEW: MFA enrollment/management
    MFAEnrollment.js      -- NEW: QR code + verify flow
    BackupCodes.js        -- NEW: Display/download backup codes
    TrustedDevices.js     -- NEW: List/revoke trusted devices
  Admin/
    MFAManagement.js      -- NEW: Admin MFA dashboard
```

---

## 7. Implementation Plan

### Phase 1: Security Fixes -- Rate Limiting, Sessions, CORS, Headers (2-3 days)

| Task | File(s) | Depends On |
|------|---------|------------|
| 1.1 Add Flask-Limiter dependency | `requirements.txt` | -- |
| 1.2 Initialize rate limiter | `backend/app/__init__.py` | 1.1 |
| 1.3 Apply rate limits to auth routes | `backend/app/routes/auth.py` | 1.2 |
| 1.4 Apply rate limits to API routes | `tickets.py`, `messages.py`, `workers.py` | 1.2 |
| 1.5 Add WebSocket rate limiting | `backend/app/socketio_handlers.py` | -- |
| 1.6 Tighten session config | `backend/config.py` | -- |
| 1.7 Add session refresh endpoint | `backend/app/routes/auth.py` | 1.6 |
| 1.8 Fix CORS: config-driven origins | `config.py`, `__init__.py` | -- |
| 1.9 Add security headers | `backend/app/__init__.py` | -- |
| 1.10 Default to production config | `backend/app/__init__.py` | -- |
| 1.11 Remove hardcoded secret fallback | `backend/config.py` | -- |
| 1.12 Add password strength validation | `backend/app/utils/auth.py`, `auth.py` | -- |
| 1.13 Frontend: Handle 429 responses | `frontend/src/services/api.js` | 1.3, 1.4 |
| 1.14 Frontend: Auto-refresh sessions | `frontend/src/services/auth.js` | 1.7 |

### Phase 2: Race Condition Fix (0.5 day)

| Task | File(s) | Depends On |
|------|---------|------------|
| 2.1 Create ticket_number_seq migration | `migrations/003_ticket_sequence.sql` | -- |
| 2.2 Update ticket creation to use sequence | `backend/app/routes/tickets.py` | 2.1 |

### Phase 3: Input Sanitization (1 day)

| Task | File(s) | Depends On |
|------|---------|------------|
| 3.1 Add bleach dependency | `requirements.txt` | -- |
| 3.2 Create sanitize utility | `backend/app/utils/sanitize.py` | 3.1 |
| 3.3 Sanitize ticket description | `backend/app/routes/tickets.py` | 3.2 |
| 3.4 Sanitize message content (REST + WS) | `messages.py`, `socketio_handlers.py` | 3.2 |
| 3.5 Sanitize search inputs | `backend/app/routes/workers.py` | 3.2 |

### Phase 4: MFA Backend (2-3 days)

| Task | File(s) | Depends On |
|------|---------|------------|
| 4.1 Add dependencies: pyotp, qrcode, cryptography | `requirements.txt` | -- |
| 4.2 Create MFA database migration | `migrations/004_mfa_tables.sql` | -- |
| 4.3 Add MFA SQLAlchemy models | `backend/app/models.py` | 4.2 |
| 4.4 Create MFA utility module | `backend/app/utils/mfa.py` | 4.1 |
| 4.5 Create MFA routes blueprint | `backend/app/routes/mfa.py` | 4.3, 4.4 |
| 4.6 Modify login route for MFA | `backend/app/routes/auth.py` | 4.5 |
| 4.7 Add admin MFA endpoints | `backend/app/routes/workers.py` or `admin.py` | 4.5 |
| 4.8 Register MFA blueprint | `backend/app/__init__.py` | 4.5 |

### Phase 5: MFA Frontend (2-3 days)

| Task | File(s) | Depends On |
|------|---------|------------|
| 5.1 Create MFAVerify component | `frontend/src/components/Auth/MFAVerify.js` | Phase 4 |
| 5.2 Modify Login component for MFA flow | `frontend/src/components/Auth/Login.js` | 5.1 |
| 5.3 Modify auth service for MFA | `frontend/src/services/auth.js` | Phase 4 |
| 5.4 Create SecuritySettings page | `frontend/src/components/Settings/SecuritySettings.js` | Phase 4 |
| 5.5 Create MFAEnrollment component | `frontend/src/components/Settings/MFAEnrollment.js` | 5.4 |
| 5.6 Create BackupCodes display component | `frontend/src/components/Settings/BackupCodes.js` | 5.5 |
| 5.7 Create TrustedDevices component | `frontend/src/components/Settings/TrustedDevices.js` | Phase 4 |
| 5.8 Add routes for settings pages | `frontend/src/App.js` | 5.4-5.7 |

### Phase 6: Admin MFA Management (1 day)

| Task | File(s) | Depends On |
|------|---------|------------|
| 6.1 Create MFAManagement admin page | `frontend/src/components/Admin/MFAManagement.js` | Phase 4, 5 |
| 6.2 Add admin route | `frontend/src/App.js` | 6.1 |
| 6.3 MFA enforcement toggle UI | Part of 6.1 | 4.7 |

**Total estimated effort: 8-11 days**

---

## 8. Test Cases

### 8.1 Rate Limiting

**TC-RL-01: Login rate limit triggers after 5 attempts**
```
Given   a user at IP 10.0.0.1
When    the user sends 6 POST requests to /api/auth/login within 60 seconds
Then    the first 5 requests return 200 or 401 (based on credentials)
And     the 6th request returns 429 with body {"error": "Rate limit exceeded", "retry_after": <seconds>}
And     after waiting 60 seconds, the next request is allowed
```

**TC-RL-02: API rate limit triggers after 100 requests**
```
Given   an authenticated user
When    the user sends 101 GET requests to /api/tickets within 1 hour
Then    the first 100 requests return 200
And     the 101st request returns 429
```

**TC-RL-03: WebSocket rate limit triggers after 50 messages**
```
Given   an authenticated user connected via WebSocket
When    the user emits 51 'send_message' events within 60 seconds
Then    the first 50 messages are processed normally
And     the 51st triggers an 'error' event with message "Rate limit exceeded"
```

**TC-RL-04: Rate limits are per-IP for unauthenticated endpoints**
```
Given   two users at different IPs
When    user A sends 5 login attempts and user B sends 5 login attempts
Then    both users can complete their 5 attempts (not sharing a limit)
```

### 8.2 Session Management

**TC-SM-01: Session expires after configured lifetime**
```
Given   an authenticated user with PERMANENT_SESSION_LIFETIME = 8 hours
When    the user makes no requests for 8 hours
Then    the next request returns 401
And     the user must log in again
```

**TC-SM-02: Session refresh extends expiration**
```
Given   an authenticated user
When    the user calls POST /api/auth/refresh at the 7-hour mark
Then    the session expiration is extended by another 8 hours
And     subsequent API calls succeed
```

**TC-SM-03: Logout invalidates session**
```
Given   an authenticated user
When    the user calls POST /api/auth/logout
Then    the session cookie is cleared
And     subsequent API calls with the old cookie return 401
```

**TC-SM-04: Session cookie has correct attributes**
```
Given   a successful login in production mode
When    the Set-Cookie header is examined
Then    it contains HttpOnly, Secure, SameSite=Lax attributes
And     the cookie name is 'hackathon_session'
```

### 8.3 CORS

**TC-CORS-01: Allowed origin succeeds**
```
Given   a request from http://localhost:3000 with Origin header
When    the request is sent to any API endpoint
Then    the response includes Access-Control-Allow-Origin: http://localhost:3000
And     Access-Control-Allow-Credentials: true
```

**TC-CORS-02: Disallowed origin is rejected**
```
Given   a request from http://evil-site.com with Origin header
When    the request is sent to any API endpoint
Then    the response does NOT include Access-Control-Allow-Origin
And     the browser blocks the response
```

**TC-CORS-03: WebSocket from disallowed origin is rejected**
```
Given   a WebSocket connection attempt from http://evil-site.com
When    the connection handshake is initiated
Then    the server rejects the connection
And     the client receives a connection error
```

### 8.4 Input Sanitization (XSS Prevention)

**TC-XSS-01: Script tags are stripped from ticket description**
```
Given   an authenticated user
When    creating a ticket with description "<script>alert('xss')</script>Normal text"
Then    the stored description is "Normal text" (script tag stripped)
And     the API response contains the sanitized text
```

**TC-XSS-02: HTML entities are stripped from chat messages**
```
Given   an authenticated user in a WebSocket chat
When    sending a message with content "<img onerror=alert(1) src=x>"
Then    the stored content has the img tag stripped
```

**TC-XSS-03: LIKE injection in search is prevented**
```
Given   an authenticated user
When    searching for workers with search="%"
Then    the search term is escaped to "\%"
And     only workers with literal "%" in their name are returned (none)
```

### 8.5 Race Conditions

**TC-RC-01: Concurrent ticket creation produces unique numbers**
```
Given   10 authenticated users
When    all 10 send POST /api/tickets simultaneously
Then    all 10 tickets are created successfully
And     all 10 have unique, sequential ticket_numbers
And     no unique constraint violations occur
```

**TC-RC-02: Ticket sequence survives server restart**
```
Given   the last ticket has ticket_number = 100
When    the server restarts and a new ticket is created
Then    the new ticket has ticket_number = 101
```

### 8.6 MFA Enrollment

**TC-MFA-01: Successful MFA enrollment**
```
Given   an authenticated user without MFA enabled
When    the user calls POST /api/auth/mfa/enroll
Then    the response contains qr_code (base64 PNG), manual_key, issuer, account
And     a user_mfa row is created with is_enabled=false
When    the user enters the correct TOTP code from their authenticator
And     calls POST /api/auth/mfa/verify-enrollment with that code
Then    the response contains 8 backup codes
And     user_mfa.is_enabled is set to true
And     an mfa_audit_log entry with action='enrolled' is created
```

**TC-MFA-02: Enrollment verification with invalid code**
```
Given   a user in the middle of MFA enrollment
When    the user calls POST /api/auth/mfa/verify-enrollment with totp_code="000000"
Then    the response is 400 with error "Invalid verification code"
And     user_mfa.is_enabled remains false
```

**TC-MFA-03: Cannot enroll when already enrolled**
```
Given   an authenticated user with MFA already enabled
When    the user calls POST /api/auth/mfa/enroll
Then    the response is 400 with error "MFA is already enabled"
```

### 8.7 MFA Login

**TC-MFA-04: Login with valid TOTP code**
```
Given   a user with MFA enabled
When    the user submits correct email + password
Then    the response is {mfa_required: true, mfa_token: "..."}
When    the user submits the mfa_token and correct TOTP code
Then    the response is 200 with full user object
And     a session cookie is set
And     an mfa_audit_log entry with action='login_success' is created
```

**TC-MFA-05: Login with invalid TOTP code**
```
Given   a user with MFA enabled who has received an mfa_token
When    the user submits the mfa_token with totp_code="000000"
Then    the response is 400 with error "Invalid verification code"
And     an mfa_audit_log entry with action='login_failed' is created
```

**TC-MFA-06: Login with expired mfa_token**
```
Given   a user with MFA enabled who received an mfa_token 6 minutes ago
When    the user submits the expired mfa_token with a correct TOTP code
Then    the response is 401 with error "MFA token expired, please login again"
```

**TC-MFA-07: TOTP code time window tolerance**
```
Given   a user with MFA enabled
When    the user submits a TOTP code that was valid 30 seconds ago (previous period)
Then    the response is 200 (one step tolerance)
When    the user submits a TOTP code from 90 seconds ago (two periods back)
Then    the response is 400 (outside tolerance window)
```

### 8.8 Backup Codes

**TC-MFA-08: Login with valid backup code**
```
Given   a user with MFA enabled and 8 backup codes
When    the user submits mfa_token + backup_code="ABCD1234" (first code)
Then    the response is 200 with backup_codes_remaining=7
And     the used backup code is marked as consumed
And     an mfa_audit_log entry with action='backup_code_used' is created
```

**TC-MFA-09: Backup code cannot be reused**
```
Given   a user who just used backup code "ABCD1234"
When    the user attempts to use "ABCD1234" again
Then    the response is 400 with error "Invalid backup code"
```

**TC-MFA-10: Backup code exhaustion warning**
```
Given   a user with 1 backup code remaining
When    the user successfully uses the last backup code
Then    the response includes backup_codes_remaining=0
And     the response includes warning "All backup codes have been used. Please generate new ones."
```

**TC-MFA-11: Regenerate backup codes**
```
Given   a user with MFA enabled and 3 backup codes remaining
When    the user calls POST /api/auth/mfa/backup-codes with correct password
Then    8 new backup codes are returned
And     the old 3 codes are invalidated
And     backup_codes_remaining is set to 8
```

### 8.9 Remember Device

**TC-MFA-12: Remember device skips MFA on next login**
```
Given   a user with MFA enabled who checked "remember device"
When    the user logs out and logs back in from the same browser
Then    the login endpoint detects the device_token cookie
And     returns the full user object (200) without requiring MFA
And     trusted_devices.last_used_at is updated
```

**TC-MFA-13: Trusted device expires after 30 days**
```
Given   a trusted device token that was created 31 days ago
When    the user attempts to login
Then    the expired token is ignored
And     MFA verification is required
And     the expired trusted_devices row is deleted
```

### 8.10 Admin MFA Management

**TC-MFA-14: Admin resets user MFA**
```
Given   an admin user
And     a user "locked@example.com" with MFA enabled who lost their phone
When    the admin calls POST /api/admin/mfa/reset/42
Then    the response is 200
And     the user_mfa row for user 42 is deleted
And     all trusted_devices for user 42 are deleted
And     an mfa_audit_log entry with action='admin_reset' is created
And     the user can now login with password only
```

**TC-MFA-15: Admin enforces MFA for all users**
```
Given   an admin sets enforcement to "required_for_all"
When    a user without MFA logs in
Then    the login response includes {mfa_setup_required: true}
And     the user is redirected to the MFA enrollment page
And     the user cannot access other pages until MFA is set up
```

**TC-MFA-16: Non-admin cannot access admin MFA endpoints**
```
Given   a user with role "hacker"
When    the user calls POST /api/admin/mfa/reset/42
Then    the response is 403 with error "Only admins can perform this action"
```

---

## 9. OWASP Compliance Validation

### OWASP Top 10 (2021) Checklist

| OWASP ID | Category | Status | Implementation |
|-----------|----------|--------|----------------|
| **A01** | Broken Access Control | **ADDRESSED** | Rate limiting on all endpoints prevents brute-force. Session management hardened with secure cookies, shorter lifetimes, and refresh mechanism. Admin-only endpoints verified with role checks. |
| **A02** | Cryptographic Failures | **ADDRESSED** | TOTP secrets encrypted at rest with AES-256-GCM. Backup codes stored as bcrypt hashes. Device tokens stored as SHA-256 hashes. SESSION_COOKIE_SECURE=True enforces HTTPS. No hardcoded secrets in production. |
| **A03** | Injection | **ADDRESSED** | All user inputs sanitized through bleach (HTML/XSS). SQLAlchemy ORM parameterizes queries. LIKE patterns escaped. Search inputs length-limited. |
| **A04** | Insecure Design | **ADDRESSED** | MFA adds defense-in-depth to authentication. PostgreSQL sequences eliminate race conditions. Backup codes prevent MFA lockout. Admin reset as recovery path. |
| **A05** | Security Misconfiguration | **ADDRESSED** | Debug mode defaults to off. CORS locked to explicit origins. Security headers added (CSP, HSTS, X-Frame-Options). SECRET_KEY required in production (no fallback). |
| **A06** | Vulnerable Components | **PARTIAL** | Dependencies should be pinned to exact versions. Recommend adding `safety` or `pip-audit` to CI/CD pipeline to scan for known vulnerabilities in Python packages. |
| **A07** | Identification & Auth Failures | **ADDRESSED** | TOTP-based MFA implemented. Rate limiting on login prevents credential stuffing. Password strength requirements added. Session fixation prevented by Flask-Login defaults. |
| **A08** | Software & Data Integrity | **LOW RISK** | Not directly applicable in current architecture. Recommendation: add SRI (Subresource Integrity) hashes to frontend script tags if using CDN. |
| **A09** | Security Logging & Monitoring | **ADDRESSED** | MFA audit log tracks all authentication events. Existing logging_config.py handles application logs. Rate limit violations logged. Recommendation: ship logs to centralized SIEM for the hackathon event. |
| **A10** | Server-Side Request Forgery | **LOW RISK** | Workday integration URLs are configuration-driven (not user-supplied). No SSRF vectors identified in current codebase. |

### Additional Security Controls

| Control | Status | Notes |
|---------|--------|-------|
| Password hashing (bcrypt) | Existing | `backend/app/utils/auth.py` uses bcrypt with auto-generated salt |
| HTTPS enforcement | Recommended | SESSION_COOKIE_SECURE=True requires HTTPS. Add HSTS header. Deploy behind TLS-terminating reverse proxy. |
| Content-Security-Policy | New | Added in security headers (Section 2.7). Prevents inline scripts. |
| Account lockout | New | After 5 failed login attempts within 1 minute, IP is rate-limited for 60 seconds. |
| Audit trail | New | mfa_audit_log table tracks all MFA-related events with IP and user-agent. |

---

## 10. Risks & Mitigations

| # | Risk | Impact | Likelihood | Mitigation |
|---|------|--------|------------|------------|
| R1 | MFA lockout: User loses phone and backup codes | **High** -- user cannot access account | Medium | Force backup code download/acknowledgment during enrollment. Admin reset capability. Display warning when backup codes are running low. |
| R2 | TOTP clock drift causes valid codes to be rejected | **Medium** -- user frustration, support load | Low | Allow +/- 1 time step tolerance (30 seconds). Display clock sync help in error messages. |
| R3 | Rate limiting blocks legitimate users during hackathon peak | **Medium** -- users unable to work | Medium | Set generous limits (100 API/hour is ~1.6/min). Whitelist admin IPs if needed. Monitor 429 rates and adjust dynamically. Use per-user limits for authenticated endpoints, not per-IP. |
| R4 | In-memory rate limit state lost on server restart | **Low** -- temporary rate limit bypass | Medium | For hackathon scale (single server), this is acceptable. For production, use Redis as Flask-Limiter backend. |
| R5 | MFA secret encryption key rotation | **Medium** -- all TOTP secrets become unreadable | Low | Store encryption key version alongside encrypted data. Support key rotation by re-encrypting all secrets during maintenance window. |
| R6 | Database migration fails on existing data | **High** -- app downtime | Low | Test migrations against production data snapshot. Include rollback scripts. Run migrations during low-traffic window. |
| R7 | Frontend XSS via React dangerouslySetInnerHTML | **High** -- stored XSS | Low | Server-side sanitization is primary defense. Also audit React components to ensure no use of `dangerouslySetInnerHTML` with user content. React's default JSX escaping provides secondary defense. |
| R8 | Trusted device cookie stolen (cookie theft) | **Medium** -- attacker bypasses MFA | Low | Device tokens are HttpOnly + Secure + SameSite=Lax. Tokens are hashed in DB (attacker with DB access can't reconstruct them). 30-day expiry limits window. Users can revoke trusted devices. |
| R9 | Hackathon WiFi network enables MITM attacks | **High** -- session hijacking | Medium | Enforce HTTPS with HSTS. SESSION_COOKIE_SECURE prevents cookie transmission over HTTP. Recommend WPA2/3 Enterprise for hackathon WiFi. |
| R10 | Performance impact of bcrypt on backup code verification | **Low** -- slight login latency | Low | Maximum 8 backup codes to compare. Each bcrypt comparison takes ~100ms. Worst case: 800ms to check all codes. Acceptable for backup code (rare) use. |

---

## Appendix A: New Dependencies

Add to `backend/requirements.txt`:

```
# Security hardening
Flask-Limiter==3.5.1
bleach==6.1.0

# MFA
pyotp==2.9.0
qrcode==7.4.2
Pillow==10.2.0         # Required by qrcode for PNG generation
cryptography==41.0.7
PyJWT==2.8.0           # For mfa_token generation
```

## Appendix B: Environment Variables (New/Modified)

```bash
# Required in production (was optional before)
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">

# New: CORS origins (comma-separated)
CORS_ORIGINS=https://hackathon.example.com

# New: MFA encryption key (AES-256)
MFA_ENCRYPTION_KEY=<generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">

# New: JWT secret for MFA tokens (can be same as SECRET_KEY)
MFA_JWT_SECRET=<separate from SECRET_KEY for defense-in-depth>

# Optional: Redis for rate limiting (default: in-memory)
RATE_LIMIT_STORAGE_URI=redis://localhost:6379/0
```

## Appendix C: File Change Summary

| File | Action | Section |
|------|--------|---------|
| `backend/requirements.txt` | MODIFY | Appendix A |
| `backend/config.py` | MODIFY | 2.2, 2.4, 2.6, 2.8 |
| `backend/app/__init__.py` | MODIFY | 2.1, 2.4, 2.6, 2.7, 4.8 |
| `backend/app/models.py` | MODIFY | 4.2 |
| `backend/app/routes/auth.py` | MODIFY | 2.1, 2.2, 4.6 |
| `backend/app/routes/tickets.py` | MODIFY | 2.3, 3.3 |
| `backend/app/routes/messages.py` | MODIFY | 2.1, 3.4 |
| `backend/app/routes/workers.py` | MODIFY | 2.1, 3.5, 4.7 |
| `backend/app/socketio_handlers.py` | MODIFY | 2.1, 3.4 |
| `backend/app/utils/auth.py` | MODIFY | 2.9 |
| `backend/app/utils/sanitize.py` | **NEW** | 2.5 |
| `backend/app/utils/mfa.py` | **NEW** | 3.4, 4.4 |
| `backend/app/routes/mfa.py` | **NEW** | 4.5, 5.x |
| `migrations/003_ticket_sequence.sql` | **NEW** | 2.3 |
| `migrations/004_mfa_tables.sql` | **NEW** | 4.1 |
| `frontend/src/services/api.js` | MODIFY | Phase 1 |
| `frontend/src/services/auth.js` | MODIFY | Phase 1, 5 |
| `frontend/src/components/Auth/Login.js` | MODIFY | Phase 5 |
| `frontend/src/components/Auth/MFAVerify.js` | **NEW** | Phase 5 |
| `frontend/src/components/Auth/BackupCodeInput.js` | **NEW** | Phase 5 |
| `frontend/src/components/Settings/SecuritySettings.js` | **NEW** | Phase 5 |
| `frontend/src/components/Settings/MFAEnrollment.js` | **NEW** | Phase 5 |
| `frontend/src/components/Settings/BackupCodes.js` | **NEW** | Phase 5 |
| `frontend/src/components/Settings/TrustedDevices.js` | **NEW** | Phase 5 |
| `frontend/src/components/Admin/MFAManagement.js` | **NEW** | Phase 6 |
| `frontend/src/App.js` | MODIFY | Phase 5, 6 |
