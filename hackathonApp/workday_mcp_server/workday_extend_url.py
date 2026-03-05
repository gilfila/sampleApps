"""
Build Workday Extend API URLs from environment variables.

URL pattern: {WORKDAY_EXTEND_BASE_URL}/apps/{WORKDAY_APP_NAME}/v1/{collection_name}
Example:     https://api.workday.com/apps/my-hackathon-app/v1/participants

Makes the code extensible: set app name and collection name per CBO (hacker vs ticket).
"""

import os

# Default base for Workday Extend API
DEFAULT_EXTEND_BASE = "https://api.workday.com"


def get_extend_base_url() -> str:
    """Return WORKDAY_EXTEND_BASE_URL from env, or default."""
    url = (os.environ.get("WORKDAY_EXTEND_BASE_URL") or "").strip().rstrip("/")
    return url or DEFAULT_EXTEND_BASE


def get_app_name() -> str | None:
    """Return WORKDAY_APP_NAME from env, or None."""
    name = (os.environ.get("WORKDAY_APP_NAME") or "").strip()
    return name or None


def build_extend_collection_url(collection_name: str) -> str | None:
    """
    Build URL for an Extend CBO collection: {base}/apps/{app_name}/v1/{collection_name}.

    Returns None if WORKDAY_APP_NAME or collection_name is missing.
    """
    base = get_extend_base_url()
    app_name = get_app_name()
    if not app_name or not (collection_name or "").strip():
        return None
    collection_name = collection_name.strip().strip("/")
    return f"{base}/apps/{app_name}/v1/{collection_name}"


def get_hacker_collection_url() -> str | None:
    """URL for hacker/participant CBO. Uses WORKDAY_HACKER_COLLECTION_NAME."""
    name = (os.environ.get("WORKDAY_HACKER_COLLECTION_NAME") or "").strip()
    return build_extend_collection_url(name) if name else None


def get_ticket_collection_url() -> str | None:
    """URL for ticket CBO. Uses WORKDAY_TICKET_COLLECTION_NAME."""
    name = (os.environ.get("WORKDAY_TICKET_COLLECTION_NAME") or "").strip()
    return build_extend_collection_url(name) if name else None
