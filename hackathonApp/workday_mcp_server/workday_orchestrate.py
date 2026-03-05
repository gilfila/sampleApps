"""
Workday Orchestrate API client for MCP.

Calls the Workday Orchestrate REST API to launch orchestrations.
URL pattern: {WORKDAY_ORCHESTRATE_BASE_URL}/orchestrate/v1/apps/{app_name}/orchestrations/{orchestration_name}/launch

Env:
  WORKDAY_ORCHESTRATE_BASE_URL — e.g. https://api.us.wcp.workday.com (no trailing slash)
  WORKDAY_ORCHESTRATE_APP_NAME — optional; default app name (e.g. hackathontickets_svfbfp)
"""

import os
from urllib.parse import urljoin

import requests


def get_orchestrate_config() -> dict[str, str]:
    """Return orchestrate base URL and default app name from environment."""
    base = (os.environ.get("WORKDAY_ORCHESTRATE_BASE_URL") or "").strip().rstrip("/")
    app_name = (os.environ.get("WORKDAY_ORCHESTRATE_APP_NAME") or "hackathontickets_svfbfp").strip()
    return {"base_url": base, "app_name": app_name}


def launch_orchestration(
    orchestration_name: str,
    access_token: str,
    *,
    app_name: str | None = None,
    json_body: dict | None = None,
    timeout: int = 60,
) -> dict:
    """
    Launch a Workday Orchestrate orchestration via POST .../launch.

    Args:
        orchestration_name: Name of the orchestration (e.g. CreateTicket).
        access_token: Bearer token from workday_auth.get_workday_bearer_token().
        app_name: Override app name; if None, uses WORKDAY_ORCHESTRATE_APP_NAME or hackathontickets_svfbfp.
        json_body: Optional JSON body sent as the launch request payload (orchestration inputs).
        timeout: Request timeout in seconds (default 60; orchestrations can take longer).

    Returns:
        JSON response from the launch endpoint.

    Raises:
        ValueError: If base URL is not set or the API returns an error.
    """
    config = get_orchestrate_config()
    base = config["base_url"]
    if not base:
        raise ValueError(
            "WORKDAY_ORCHESTRATE_BASE_URL is not set in .env (e.g. https://api.us.wcp.workday.com)."
        )
    app = (app_name or config["app_name"]).strip()
    if not app:
        raise ValueError("Orchestration app name is required (set WORKDAY_ORCHESTRATE_APP_NAME or pass app_name).")
    if not orchestration_name or not str(orchestration_name).strip():
        raise ValueError("orchestration_name is required.")

    path = f"orchestrate/v1/apps/{app}/orchestrations/{orchestration_name.strip()}/launch"
    url = urljoin(base + "/", path)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    if json_body is not None:
        headers["Content-Type"] = "application/json"

    response = requests.post(
        url,
        json=json_body,
        headers=headers,
        timeout=timeout,
    )
    if not response.ok:
        raise ValueError(
            f"Workday Orchestrate launch error: {response.status_code} {response.reason}. "
            f"Details: {response.text[:1000]}"
        )
    return response.json() if response.content else {}
