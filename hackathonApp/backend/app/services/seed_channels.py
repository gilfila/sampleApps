"""Seed default channels (Get-Help and General) on deploy.

These channels always exist and are not user-created. All workers are added as members.
"""

import logging
from app import db
from app.models import Channel, ChannelType, ChannelMember, Worker, WorkerRole

logger = logging.getLogger(__name__)

# Display names for the two default channels (must match exactly for agent wiring)
DEFAULT_CHANNEL_NAMES = ("General", "Get-Help")
GET_HELP_CHANNEL_NAME = "Get-Help"

# Email for the system worker used as channel creator and agent sender
SYSTEM_WORKER_EMAIL = "system@internal"


def get_or_create_system_worker():
    """Get or create the system worker (used as channel creator and agent sender)."""
    w = Worker.query.filter_by(email=SYSTEM_WORKER_EMAIL).first()
    if w:
        return w
    w = Worker(
        workday_id=None,
        email=SYSTEM_WORKER_EMAIL,
        name="System",
        password_hash=None,
        role=WorkerRole.HACKER,
        is_active=False,
    )
    db.session.add(w)
    db.session.flush()
    logger.info("Created system worker for default channels and agent")
    return w


def seed_default_channels():
    """
    Create Get-Help and General channels if they do not exist.
    Uses a system worker as created_by. Adds all non-system workers as members.
    """
    system = get_or_create_system_worker()
    db.session.commit()

    for name in DEFAULT_CHANNEL_NAMES:
        ch = Channel.query.filter_by(name=name).first()
        if ch:
            logger.debug("Default channel %s already exists", name)
            continue
        ch = Channel(
            name=name,
            description=f"Default channel: {name}." if name == "General" else "Get help and create tickets. The assistant can respond here.",
            channel_type=ChannelType.PUBLIC,
            created_by_id=system.id,
        )
        db.session.add(ch)
        db.session.flush()
        logger.info("Created default channel: %s", name)

        # Add all workers (except system) as members
        for worker in Worker.query.filter(Worker.id != system.id).all():
            if ChannelMember.query.filter_by(channel_id=ch.id, worker_id=worker.id).first():
                continue
            db.session.add(ChannelMember(channel_id=ch.id, worker_id=worker.id))

    db.session.commit()


def get_system_worker():
    """Return the system worker (for agent replies). Call after seed_default_channels has run."""
    return Worker.query.filter_by(email=SYSTEM_WORKER_EMAIL).first()
