import logging

logger = logging.getLogger(__name__)


# TODO: Re-enable Workday sync when a business object is ready.
# The integration scaffolding lives in workday_ticket_sync.py.
# The Ticket model already has workday_ticket_id, sync_status,
# last_synced_at, and sync_error columns reserved for this purpose.


class TicketService:
    """Service for ticket business logic.

    Workday sync is currently disabled. Tickets are stored locally in
    PostgreSQL as the source of truth.
    """
    pass
