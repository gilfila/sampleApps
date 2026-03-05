from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import Index
from enum import Enum

# Import db from app package - will be set in __init__.py
from app import db


class TicketStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"
    DUPLICATE = "duplicate"


class TicketPriority(Enum):
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class SyncStatus(Enum):
    PENDING = "pending"
    SYNCED = "synced"
    ERROR = "error"


class MessageType(Enum):
    DIRECT = "direct"
    GROUP = "group"
    CHANNEL = "channel"
    TICKET_THREAD = "ticket_thread"


class WorkerRole(Enum):
    HACKER = "hacker"
    EXPERT = "expert"
    ADMIN = "admin"


# --- Workday Ad-Hoc Sync enums ---

class WorkerSyncStatus(Enum):
    NEVER_SYNCED = "never_synced"
    SYNCED = "synced"
    STALE = "stale"
    ERROR = "error"


class SyncJobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class SyncTriggerType(Enum):
    MANUAL = "manual"
    BULK = "bulk"
    FIRST_LOGIN = "first_login"
    STALE_LOGIN = "stale_login"


class Worker(db.Model, UserMixin):
    """Worker model synced from Workday"""
    __tablename__ = 'workers'

    id = db.Column(db.Integer, primary_key=True)
    workday_id = db.Column(db.String(255), unique=True, nullable=True, index=True)  # null = local-only user
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    employee_id = db.Column(db.String(255))
    department = db.Column(db.String(255))
    job_title = db.Column(db.String(255))
    manager = db.Column(db.String(255))

    # Hacker-specific fields from Workday custom object
    table = db.Column(db.String(50))
    team_name = db.Column(db.String(255))
    tenant_url = db.Column(db.String(500))
    company = db.Column(db.String(255))

    # App-specific fields
    role = db.Column(db.Enum(WorkerRole), default=WorkerRole.HACKER, nullable=False)
    password_hash = db.Column(db.String(255))  # For session-based auth
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Sync-tracking columns (Workday ad-hoc sync; migration 005)
    last_synced_at = db.Column(db.DateTime, nullable=True)
    sync_status = db.Column(db.String(20), default='never_synced', nullable=True)
    sync_error = db.Column(db.Text, nullable=True)

    # Relationships
    reported_tickets = db.relationship('Ticket', foreign_keys='Ticket.reporter_id', backref='reporter', lazy='dynamic')
    assigned_tickets = db.relationship('Ticket', foreign_keys='Ticket.assignee_id', backref='assignee', lazy='dynamic')
    sent_messages = db.relationship('ChatMessage', foreign_keys='ChatMessage.sender_id', backref='sender', lazy='dynamic')
    expert_assignments = db.relationship('ExpertAssignment', foreign_keys='ExpertAssignment.worker_id', backref='worker', lazy='dynamic')

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return f'<Worker {self.email}>'


class Ticket(db.Model):
    """Ticket model - local DB is the source of truth.
    TODO: Eventually persist tickets to a Workday business object.
    The workday_ticket_id, sync_status, last_synced_at, and sync_error
    columns are reserved for that future integration.
    """
    __tablename__ = 'tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    workday_ticket_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
    ticket_number = db.Column(db.Integer, unique=True, nullable=False, index=True)
    
    reporter_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location_table = db.Column(db.String(50))
    status = db.Column(db.Enum(TicketStatus), default=TicketStatus.OPEN, nullable=False, index=True)
    priority = db.Column(db.Enum(TicketPriority), default=TicketPriority.NORMAL, nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=True)
    time_to_closed = db.Column(db.String(50))
    ticket_opened = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ticket_closed = db.Column(db.DateTime, nullable=True)
    ticket_thread_link = db.Column(db.String(500))
    
    # Sync status fields
    sync_status = db.Column(db.Enum(SyncStatus), default=SyncStatus.PENDING, nullable=False, index=True)
    last_synced_at = db.Column(db.DateTime, nullable=True)
    sync_error = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_ticket_status_created', 'status', 'created_at'),
        Index('idx_ticket_sync_status', 'sync_status', 'updated_at'),
    )
    
    def __repr__(self):
        return f'<Ticket {self.ticket_number}>'


class ChatMessage(db.Model):
    """Chat message model"""
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.Enum(MessageType), nullable=False, index=True)
    
    # Context fields based on message type
    thread_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=True)  # For ticket threads
    channel_id = db.Column(db.String(255), nullable=True, index=True)  # For channels/groups
    group_id = db.Column(db.String(255), nullable=True, index=True)  # For group chats
    recipient_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=True)  # For direct messages
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_message_type_timestamp', 'message_type', 'timestamp'),
        Index('idx_thread_timestamp', 'thread_id', 'timestamp'),
    )
    
    def __repr__(self):
        return f'<ChatMessage {self.id}>'


class ChatLog(db.Model):
    """Chat log for error handling and audit"""
    __tablename__ = 'chat_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(100), nullable=False, index=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=True)
    details = db.Column(db.Text)
    error_message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f'<ChatLog {self.id} - {self.event_type}>'


class ExpertAssignment(db.Model):
    """Expert role assignment for manual expert management"""
    __tablename__ = 'expert_assignments'

    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=False)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    assigned_by = db.relationship('Worker', foreign_keys=[assigned_by_id], backref='assignments_made')

    def __repr__(self):
        return f'<ExpertAssignment {self.worker_id}>'


# --- Workday Ad-Hoc Sync Models ---

class SyncJob(db.Model):
    """Tracks every sync operation for audit purposes."""
    __tablename__ = 'sync_jobs'

    id = db.Column(db.String(36), primary_key=True)  # UUID
    trigger_type = db.Column(db.Enum(SyncTriggerType), nullable=False)
    initiated_by_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=True)

    status = db.Column(db.Enum(SyncJobStatus), default=SyncJobStatus.PENDING, nullable=False)
    started_at = db.Column(db.DateTime, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    total_count = db.Column(db.Integer, default=0)
    success_count = db.Column(db.Integer, default=0)
    error_count = db.Column(db.Integer, default=0)
    skip_count = db.Column(db.Integer, default=0)

    filter_criteria = db.Column(db.JSON, nullable=True)
    error_summary = db.Column(db.Text, nullable=True)

    # Relationships
    initiated_by = db.relationship('Worker', foreign_keys=[initiated_by_id])
    items = db.relationship('SyncJobItem', backref='job', lazy='dynamic')

    __table_args__ = (
        Index('idx_sync_job_status_started', 'status', 'started_at'),
        Index('idx_sync_job_trigger', 'trigger_type', 'started_at'),
    )


class SyncJobItem(db.Model):
    """Per-worker result within a sync job."""
    __tablename__ = 'sync_job_items'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(36), db.ForeignKey('sync_jobs.id'), nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=True)
    workday_id = db.Column(db.String(255), nullable=False)

    status = db.Column(db.String(20), nullable=False)  # synced, skipped, error
    changed_fields = db.Column(db.JSON, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    synced_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_sync_item_job_status', 'job_id', 'status'),
    )


# --- MFA Models ---

class UserMFA(db.Model):
    """MFA configuration for a user."""
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
    """Trusted device for MFA remember-me."""
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
    """Audit log for MFA events."""
    __tablename__ = 'mfa_audit_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('workers.id', ondelete='CASCADE'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class AppSetting(db.Model):
    """Application-wide settings."""
    __tablename__ = 'app_settings'

    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.JSON, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=True)


# ---------------------------------------------------------------------------
# Chat Models — Channels & Direct-Message Conversations
# ---------------------------------------------------------------------------

class ChannelType(Enum):
    PUBLIC = "public"
    PRIVATE = "private"


class Channel(db.Model):
    """A chat channel (public or private)."""
    __tablename__ = 'channels'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False, index=True)
    description = db.Column(db.String(500), default='')
    channel_type = db.Column(db.Enum(ChannelType), default=ChannelType.PUBLIC, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    created_by = db.relationship('Worker', foreign_keys=[created_by_id])
    members = db.relationship('ChannelMember', backref='channel', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Channel #{self.name}>'


class ChannelMember(db.Model):
    """Tracks which workers belong to which channels."""
    __tablename__ = 'channel_members'

    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id', ondelete='CASCADE'), nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id', ondelete='CASCADE'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('channel_id', 'worker_id', name='uq_channel_member'),
        Index('idx_channel_member_worker', 'worker_id'),
    )


class Conversation(db.Model):
    """A direct-message conversation between exactly two users.

    The canonical key is (user_a_id, user_b_id) where user_a_id < user_b_id
    so we can guarantee a single row per pair.
    """
    __tablename__ = 'conversations'

    id = db.Column(db.Integer, primary_key=True)
    user_a_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=False)
    user_b_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user_a = db.relationship('Worker', foreign_keys=[user_a_id])
    user_b = db.relationship('Worker', foreign_keys=[user_b_id])

    __table_args__ = (
        db.UniqueConstraint('user_a_id', 'user_b_id', name='uq_conversation_pair'),
        Index('idx_conversation_users', 'user_a_id', 'user_b_id'),
    )
