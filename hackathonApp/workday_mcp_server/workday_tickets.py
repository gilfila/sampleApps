"""
Workday Tickets business object client for MCP.

Ticket base URL is resolved in this order:
1) Extend pattern: WORKDAY_EXTEND_BASE_URL + WORKDAY_APP_NAME + WORKDAY_TICKET_COLLECTION_NAME
   → {base}/apps/{app_name}/v1/{collection_name}
2) Explicit: WORKDAY_TICKETS_BUSINESS_OBJECT_URL
"""

import os
import logging
from urllib.parse import urljoin

import requests

from workday_extend_url import get_ticket_collection_url

logger = logging.getLogger(__name__)


def get_tickets_base_url() -> str | None:
    """Return ticket CBO base URL: from Extend vars (app + collection) or WORKDAY_TICKETS_BUSINESS_OBJECT_URL."""
    extend_url = get_ticket_collection_url()
    if extend_url:
        return extend_url
    url = (os.environ.get("WORKDAY_TICKETS_BUSINESS_OBJECT_URL") or "").strip()
    return url or None


def _ticket_request(
    method: str,
    access_token: str,
    path: str = "",
    *,
    json_body: dict | None = None,
    timeout: int = 30,
) -> dict | list:
    """Perform authenticated request to the tickets business object URL."""
    base = get_tickets_base_url()
    if not base:
        raise ValueError(
            "Ticket API URL is not set. Set WORKDAY_EXTEND_BASE_URL, WORKDAY_APP_NAME, and "
            "WORKDAY_TICKET_COLLECTION_NAME, or WORKDAY_TICKETS_BUSINESS_OBJECT_URL in .env."
        )
    url = urljoin(base.rstrip("/") + "/", path.strip("/")) if path else base
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    response = requests.request(
        method,
        url,
        headers=headers,
        json=json_body,
        timeout=timeout,
    )
    if not response.ok:
        raise ValueError(
            f"Workday tickets API error: {response.status_code} {response.reason}. "
            f"Details: {response.text[:500]}"
        )
    return response.json() if response.content else {}


def _normalize_entries(data) -> list:
    """Extract list of ticket entries from API response (Report_Entry, data, or items)."""
    entries = data.get("Report_Entry") or data.get("data") or data.get("items") or []
    if isinstance(data.get("data"), list):
        entries = data["data"]
    if isinstance(entries, dict):
        entries = list(entries.values()) if entries else []
    return list(entries) if entries else []


def list_tickets(access_token: str) -> list[dict]:
    """GET list of tickets from Workday. Returns list of ticket dicts."""
    data = _ticket_request("GET", access_token)
    entries = _normalize_entries(data) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    return [e for e in entries if e]


def get_ticket(workday_ticket_id: str, access_token: str) -> dict | None:
    """GET a single ticket by Workday ID. Returns None if 404."""
    base = get_tickets_base_url()
    if not base or not workday_ticket_id:
        return None
    try:
        data = _ticket_request("GET", access_token, str(workday_ticket_id).strip())
        return data if isinstance(data, dict) else None
    except ValueError as e:
        if "404" in str(e):
            return None
        raise


def create_ticket(access_token: str, payload: dict) -> dict:
    """POST a new ticket. Payload should include Ticket_Number, Description, Status, etc."""
    return _ticket_request("POST", access_token, json_body=payload)


def update_ticket(workday_ticket_id: str, access_token: str, payload: dict) -> dict:
    """PUT update an existing ticket by Workday ID."""
    return _ticket_request("PUT", access_token, path=str(workday_ticket_id).strip(), json_body=payload)
