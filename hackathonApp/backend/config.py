import os
from datetime import timedelta


def _pg_uri_for_sqlalchemy(url: str | None) -> str | None:
    """Ensure PostgreSQL URL uses postgresql:// (SQLAlchemy 1.4+); accept postgres:// from some hosts."""
    if not url:
        return None
    if url.startswith("postgres://"):
        return "postgresql://" + url[11:]
    return url


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True

    # Workday Integration
    WORKDAY_TENANT = os.environ.get('WORKDAY_TENANT')
    WORKDAY_CLIENT_ID = os.environ.get('WORKDAY_CLIENT_ID')
    WORKDAY_CLIENT_SECRET = os.environ.get('WORKDAY_CLIENT_SECRET')
    WORKDAY_REFRESH_TOKEN = os.environ.get('WORKDAY_REFRESH_TOKEN')
    # Extend URL pattern: {WORKDAY_EXTEND_BASE_URL}/apps/{WORKDAY_APP_NAME}/v1/{collection_name}
    _extend_base = (os.environ.get('WORKDAY_EXTEND_BASE_URL') or '').strip().rstrip('/')
    WORKDAY_EXTEND_BASE_URL = _extend_base or 'https://api.workday.com'
    WORKDAY_APP_NAME = os.environ.get('WORKDAY_APP_NAME')
    WORKDAY_HACKER_COLLECTION_NAME = os.environ.get('WORKDAY_HACKER_COLLECTION_NAME')
    WORKDAY_TICKET_COLLECTION_NAME = os.environ.get('WORKDAY_TICKET_COLLECTION_NAME')
    WORKDAY_CUSTOM_OBJECT_NAME = os.environ.get('WORKDAY_CUSTOM_OBJECT_NAME')
    WORKDAY_TICKET_CUSTOM_OBJECT_NAME = os.environ.get('WORKDAY_TICKET_CUSTOM_OBJECT_NAME')
    WORKDAY_SYNC_INTERVAL = int(os.environ.get('WORKDAY_SYNC_INTERVAL', 3600))  # seconds
    WORKDAY_TICKET_SYNC_INTERVAL = int(os.environ.get('WORKDAY_TICKET_SYNC_INTERVAL', 300))  # seconds
    WORKDAY_TICKET_SYNC_RETRY_ATTEMPTS = int(os.environ.get('WORKDAY_TICKET_SYNC_RETRY_ATTEMPTS', 3))

    # Session configuration -- tightened for security
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = 'hackathon_session'
    REMEMBER_COOKIE_DURATION = timedelta(hours=8)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = True

    # CORS -- config-driven origins (no more wildcards)
    CORS_ORIGINS = os.environ.get(
        'CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000'
    ).split(',')

    # Socket.IO
    SOCKETIO_CORS_ORIGINS = os.environ.get('SOCKETIO_CORS_ORIGINS', '*')

    # Pagination
    TICKETS_PER_PAGE = 20
    MESSAGES_PER_PAGE = 50

    # Workday Ad-Hoc Sync
    SYNC_CACHE_TTL_IDENTITY = int(os.environ.get('SYNC_CACHE_TTL_IDENTITY', 14400))  # 4 hours
    SYNC_CACHE_TTL_HACKATHON = int(os.environ.get('SYNC_CACHE_TTL_HACKATHON', 3600))  # 1 hour
    SYNC_BULK_BATCH_SIZE = int(os.environ.get('SYNC_BULK_BATCH_SIZE', 50))
    SYNC_CIRCUIT_BREAKER_THRESHOLD = int(os.environ.get('SYNC_CIRCUIT_BREAKER_THRESHOLD', 5))
    SYNC_CIRCUIT_BREAKER_COOLDOWN = int(os.environ.get('SYNC_CIRCUIT_BREAKER_COOLDOWN', 300))

    # MFA
    MFA_ENCRYPTION_KEY = os.environ.get('MFA_ENCRYPTION_KEY')
    MFA_JWT_SECRET = os.environ.get('MFA_JWT_SECRET', SECRET_KEY)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    # Allow a dev-only fallback secret so local development works without env vars
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-only-secret-not-for-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///hackathon_app.db'
    SESSION_COOKIE_SECURE = False  # Allow HTTP in development
    REMEMBER_COOKIE_SECURE = False
    # Dev-only MFA key (32 bytes hex = 64 hex chars) -- NOT for production
    MFA_ENCRYPTION_KEY = os.environ.get('MFA_ENCRYPTION_KEY') or 'a' * 64
    MFA_JWT_SECRET = os.environ.get('MFA_JWT_SECRET') or SECRET_KEY


class ProductionConfig(Config):
    """Production configuration (used on Render via FLASK_ENV=production)."""
    DEBUG = False
    _db_url = os.environ.get('DATABASE_URL')
    # Normalize postgres:// to postgresql:// for SQLAlchemy (Render often provides postgres://)
    SQLALCHEMY_DATABASE_URI = _pg_uri_for_sqlalchemy(_db_url) if _db_url else None
    DATABASE_URL = _db_url  # For create_app production validation


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SECRET_KEY = 'testing-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    MFA_ENCRYPTION_KEY = 'b' * 64  # 32 bytes in hex for test use
    MFA_JWT_SECRET = 'testing-mfa-jwt-secret'
