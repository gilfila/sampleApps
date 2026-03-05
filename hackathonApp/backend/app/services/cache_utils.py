"""Cache staleness detection utilities for Workday sync."""

from datetime import datetime, timedelta
from config import Config


def is_worker_stale(worker):
    """Check if a worker's cached data is stale based on TTL."""
    last_synced = getattr(worker, 'last_synced_at', None)
    if last_synced is None:
        return True

    ttl = timedelta(seconds=Config.SYNC_CACHE_TTL_HACKATHON)
    return datetime.utcnow() - last_synced > ttl


def staleness_info(worker):
    """Return staleness metadata for API responses.
    Safe when Worker model does not yet have last_synced_at (e.g. column not migrated).
    """
    last_synced = getattr(worker, 'last_synced_at', None)
    if last_synced is None:
        return {
            'is_stale': True,
            'last_synced_at': None,
            'staleness_message': 'Never synced from Workday'
        }

    stale = is_worker_stale(worker)
    age = datetime.utcnow() - last_synced

    if age.total_seconds() < 60:
        age_str = 'just now'
    elif age.total_seconds() < 3600:
        age_str = f'{int(age.total_seconds() / 60)} minutes ago'
    else:
        age_str = f'{int(age.total_seconds() / 3600)} hours ago'

    return {
        'is_stale': stale,
        'last_synced_at': last_synced.isoformat(),
        'staleness_message': f'Last synced {age_str}' if not stale else f'Data may be outdated (last synced {age_str})'
    }
