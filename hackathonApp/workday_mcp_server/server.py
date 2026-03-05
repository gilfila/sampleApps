"""
Workday MCP Server — Model Context Protocol server for Workday.

Uses SOAP (Staffing/Human_Resources Get_Workers) for get_worker_profile.
Run over stdio for use with MCP clients (e.g. Claude Desktop, Cursor).
"""

import json
import logging
import os
import re
import sys

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Ensure script directory is on path when run by MCP clients with full path
_load_dir = os.path.dirname(os.path.abspath(__file__))
if _load_dir not in sys.path:
    sys.path.insert(0, _load_dir)

load_dotenv(dotenv_path=os.path.join(_load_dir, ".env"))

from workday_auth import get_workday_bearer_token
from workday_rest import get_rest_config, get_worker as get_worker_rest
from workday_soap import get_worker_via_soap
from workday_tickets import (
    get_tickets_base_url,
    list_tickets as workday_list_tickets,
    get_ticket as workday_get_ticket,
    create_ticket as workday_create_ticket,
    update_ticket as workday_update_ticket,
)
from workday_orchestrate import get_orchestrate_config, launch_orchestration

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

mcp = FastMCP("Workday MCP Server")


def _ensure_token() -> str:
    """Get a valid Bearer token; refresh if expired."""
    return get_workday_bearer_token()


def _worker_id_type(worker_id: str) -> str:
    """Infer ID type: WID (UUID-like) or Employee_ID (numeric/alphanumeric)."""
    if re.match(r"^[0-9a-fA-F\-]{32,}$", worker_id.replace("-", "")):
        return "WID"
    return "Employee_ID"


def _get_worker_from_workday(employee_id: str) -> dict:
    """
    Fetch worker from Workday: use REST when WORKDAY_REST_BASE_URL is set, else SOAP.
    """
    token = _ensure_token()
    config = get_rest_config()
    if config.get("base_url") and config.get("tenant"):
        try:
            return get_worker_rest(employee_id, token)
        except ValueError:
            token = get_workday_bearer_token(force_refresh=True)
            return get_worker_rest(employee_id, token)
    # Fallback: SOAP
    id_type = _worker_id_type(employee_id)
    try:
        return get_worker_via_soap(
            worker_id=employee_id,
            access_token=token,
            id_type=id_type,
        )
    except ValueError:
        token = get_workday_bearer_token(force_refresh=True)
        return get_worker_via_soap(
            worker_id=employee_id,
            access_token=token,
            id_type=id_type,
        )


@mcp.tool()
def get_worker_profile(employee_id: str) -> str:
    """
    Fetch a worker's profile from Workday by employee ID.

    Uses REST API when WORKDAY_REST_BASE_URL and WORKDAY_TENANT are set (recommended);
    otherwise falls back to SOAP (Get_Workers). Returns the worker data as JSON.

    Args:
        employee_id: The Workday worker ID (WID, e.g. UUID, or Employee_ID).

    Returns:
        JSON string of the worker profile from the SOAP response.
    """
    if not employee_id or not str(employee_id).strip():
        return json.dumps({"error": "employee_id is required and cannot be empty"})

    employee_id = str(employee_id).strip()

    try:
        _ensure_token()
    except ValueError as e:
        logger.warning("Token failure: %s", e)
        return json.dumps({"error": "Authentication failed", "detail": str(e)})

    try:
        data = _get_worker_from_workday(employee_id)
        return json.dumps(data, indent=2)
    except ValueError as e:
        logger.warning("Workday API failure for %s: %s", employee_id, e)
        return json.dumps({"error": str(e)})
    except requests.RequestException as e:
        logger.warning("Request failed for %s: %s", employee_id, e)
        return json.dumps({"error": f"Request failed: {e}"})


# --- Workday Ticket tools (require Extend vars or WORKDAY_TICKETS_BUSINESS_OBJECT_URL in .env) ---


def _tickets_configured() -> bool:
    return bool(get_tickets_base_url())


def _tickets_token() -> str:
    return _ensure_token()


@mcp.tool()
def get_tickets() -> str:
    """
    List all tickets from the Workday tickets business object.

    Requires Extend vars (WORKDAY_APP_NAME, WORKDAY_TICKET_COLLECTION_NAME) or WORKDAY_TICKETS_BUSINESS_OBJECT_URL in .env.
    Returns JSON array of ticket objects, or an error message if not configured.
    """
    if not _tickets_configured():
        return json.dumps({
            "error": "Ticket integration not configured",
            "detail": "Set WORKDAY_EXTEND_BASE_URL, WORKDAY_APP_NAME, and WORKDAY_TICKET_COLLECTION_NAME, or WORKDAY_TICKETS_BUSINESS_OBJECT_URL in .env to use ticket tools.",
        })
    try:
        token = _tickets_token()
        tickets = workday_list_tickets(token)
        return json.dumps(tickets, indent=2)
    except ValueError as e:
        logger.warning("get_tickets failed: %s", e)
        return json.dumps({"error": str(e)})
    except requests.RequestException as e:
        logger.warning("get_tickets request failed: %s", e)
        return json.dumps({"error": f"Request failed: {e}"})


@mcp.tool()
def get_ticket(workday_ticket_id: str) -> str:
    """
    Get a single ticket from Workday by its Workday ticket ID.

    Args:
        workday_ticket_id: The Workday business object ID of the ticket.

    Returns:
        JSON object of the ticket, or error if not found / not configured.
    """
    if not _tickets_configured():
        return json.dumps({
            "error": "Ticket integration not configured",
            "detail": "Set WORKDAY_EXTEND_BASE_URL, WORKDAY_APP_NAME, and WORKDAY_TICKET_COLLECTION_NAME, or WORKDAY_TICKETS_BUSINESS_OBJECT_URL in .env to use ticket tools.",
        })
    if not workday_ticket_id or not str(workday_ticket_id).strip():
        return json.dumps({"error": "workday_ticket_id is required"})
    try:
        token = _tickets_token()
        ticket = workday_get_ticket(str(workday_ticket_id).strip(), token)
        if ticket is None:
            return json.dumps({"error": "Ticket not found", "workday_ticket_id": workday_ticket_id})
        return json.dumps(ticket, indent=2)
    except ValueError as e:
        logger.warning("get_ticket %s failed: %s", workday_ticket_id, e)
        return json.dumps({"error": str(e)})
    except requests.RequestException as e:
        logger.warning("get_ticket request failed: %s", e)
        return json.dumps({"error": f"Request failed: {e}"})


@mcp.tool()
def create_ticket(
    ticket_number: str | int,
    description: str,
    status: str = "open",
    priority: str = "normal",
    reporter_workday_id: str | None = None,
    assignee_workday_id: str | None = None,
    location_table: str | None = None,
) -> str:
    """
    Create a new ticket in the Workday tickets business object.

    Args:
        ticket_number: Ticket number (numeric or string).
        description: Ticket description.
        status: open | in_progress | closed | duplicate (default: open).
        priority: normal | high | urgent (default: normal).
        reporter_workday_id: Optional Workday ID of the reporter.
        assignee_workday_id: Optional Workday ID of the assignee.
        location_table: Optional location/table.

    Returns:
        JSON of the created ticket from Workday, or error if not configured.
    """
    if not _tickets_configured():
        return json.dumps({
            "error": "Ticket integration not configured",
            "detail": "Set WORKDAY_EXTEND_BASE_URL, WORKDAY_APP_NAME, and WORKDAY_TICKET_COLLECTION_NAME, or WORKDAY_TICKETS_BUSINESS_OBJECT_URL in .env to use ticket tools.",
        })
    if not description or not str(description).strip():
        return json.dumps({"error": "description is required"})
    payload = {
        "Ticket_Number": ticket_number,
        "Description": str(description).strip(),
        "Status": (status or "open").strip().lower(),
        "Priority": (priority or "normal").strip().lower(),
        "Reporter_Workday_ID": (reporter_workday_id or "").strip() or None,
        "Assignee_Workday_ID": (assignee_workday_id or "").strip() or None,
        "Location_Table": (location_table or "").strip() or None,
    }
    try:
        token = _tickets_token()
        result = workday_create_ticket(token, payload)
        return json.dumps(result, indent=2)
    except ValueError as e:
        logger.warning("create_ticket failed: %s", e)
        return json.dumps({"error": str(e)})
    except requests.RequestException as e:
        logger.warning("create_ticket request failed: %s", e)
        return json.dumps({"error": f"Request failed: {e}"})


# --- Workday Orchestrate: launch CreateTicket orchestration ---


def _orchestrate_configured() -> bool:
    return bool(get_orchestrate_config().get("base_url"))


@mcp.tool()
def launch_create_ticket_orchestration(
    reporter: str,
    description: str,
    status: str,
    priority: str,
    table_number: str,
    assignee: str | None = None,
) -> str:
    """
    Launch the Workday CreateTicket orchestration via the Orchestrate API.

    Calls: {base}/orchestrate/v1/apps/hackathontickets_svfbfp/orchestrations/CreateTicket/launch
    Requires WORKDAY_ORCHESTRATE_BASE_URL in .env (e.g. https://api.us.wcp.workday.com).

    Sends a payload with: reporter, description, status, priority, tableNumber; assignee is optional.

    Args:
        reporter: Reporter email or identifier (e.g. hacker@hackathon.com). Required.
        description: Ticket description. Required.
        status: Ticket status (e.g. OPEN). Required.
        priority: Priority (e.g. HIGH). Required.
        table_number: Table number (e.g. 42). Required.
        assignee: Optional assignee email or identifier (e.g. expert@hackathon.com).

    Returns:
        JSON response from the orchestration launch endpoint, or error if not configured.
    """
    if not _orchestrate_configured():
        return json.dumps({
            "error": "Orchestrate integration not configured",
            "detail": "Set WORKDAY_ORCHESTRATE_BASE_URL in .env (e.g. https://api.us.wcp.workday.com) to use this tool.",
        })
    if not (reporter and str(reporter).strip()):
        return json.dumps({"error": "reporter is required"})
    if not (description and str(description).strip()):
        return json.dumps({"error": "description is required"})
    if not (status and str(status).strip()):
        return json.dumps({"error": "status is required"})
    if not (priority and str(priority).strip()):
        return json.dumps({"error": "priority is required"})
    if not (table_number and str(table_number).strip()):
        return json.dumps({"error": "table_number is required"})

    body = {
        "reporter": str(reporter).strip(),
        "description": str(description).strip(),
        "status": str(status).strip().upper(),
        "priority": str(priority).strip().upper(),
        "tableNumber": str(table_number).strip(),
    }
    if assignee and str(assignee).strip():
        body["assignee"] = str(assignee).strip()

    try:
        token = _ensure_token()
        result = launch_orchestration(
            "CreateTicket",
            token,
            app_name="hackathontickets_svfbfp",
            json_body=body,
        )
        return json.dumps(result, indent=2)
    except ValueError as e:
        logger.warning("launch_create_ticket_orchestration failed: %s", e)
        return json.dumps({"error": str(e)})
    except requests.RequestException as e:
        logger.warning("launch_create_ticket_orchestration request failed: %s", e)
        return json.dumps({"error": f"Request failed: {e}"})


@mcp.tool()
def update_ticket(
    workday_ticket_id: str,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    assignee_workday_id: str | None = None,
    location_table: str | None = None,
) -> str:
    """
    Update an existing ticket in Workday by its Workday ticket ID.

    Args:
        workday_ticket_id: The Workday business object ID of the ticket.
        description: Optional new description.
        status: Optional new status (open | in_progress | closed | duplicate).
        priority: Optional new priority (normal | high | urgent).
        assignee_workday_id: Optional Workday ID of the assignee.
        location_table: Optional location/table.

    Returns:
        JSON of the updated ticket from Workday, or error if not configured / not found.
    """
    if not _tickets_configured():
        return json.dumps({
            "error": "Ticket integration not configured",
            "detail": "Set WORKDAY_EXTEND_BASE_URL, WORKDAY_APP_NAME, and WORKDAY_TICKET_COLLECTION_NAME, or WORKDAY_TICKETS_BUSINESS_OBJECT_URL in .env to use ticket tools.",
        })
    if not workday_ticket_id or not str(workday_ticket_id).strip():
        return json.dumps({"error": "workday_ticket_id is required"})
    payload = {}
    if description is not None:
        payload["Description"] = str(description).strip()
    if status is not None:
        payload["Status"] = str(status).strip().lower()
    if priority is not None:
        payload["Priority"] = str(priority).strip().lower()
    if assignee_workday_id is not None:
        payload["Assignee_Workday_ID"] = str(assignee_workday_id).strip() or None
    if location_table is not None:
        payload["Location_Table"] = str(location_table).strip() or None
    if not payload:
        return json.dumps({"error": "At least one field to update is required"})
    try:
        token = _tickets_token()
        result = workday_update_ticket(str(workday_ticket_id).strip(), token, payload)
        return json.dumps(result, indent=2)
    except ValueError as e:
        logger.warning("update_ticket %s failed: %s", workday_ticket_id, e)
        return json.dumps({"error": str(e)})
    except requests.RequestException as e:
        logger.warning("update_ticket request failed: %s", e)
        return json.dumps({"error": f"Request failed: {e}"})


def main() -> None:
    """Run the MCP server over stdio (default transport)."""
    mcp.run()


if __name__ == "__main__":
    main()
