"""
Workday REST API client.

Supports two URL patterns:

1) Extend (preferred when set): {WORKDAY_EXTEND_BASE_URL}/apps/{WORKDAY_APP_NAME}/v1/{WORKDAY_HACKER_COLLECTION_NAME}
   Example: https://api.workday.com/apps/my-app/v1/participants

2) Legacy CCX: WORKDAY_REST_BASE_URL + WORKDAY_TENANT, path staffing/v7/{tenant}/workers/...

Env:
  Extend: WORKDAY_EXTEND_BASE_URL, WORKDAY_APP_NAME, WORKDAY_HACKER_COLLECTION_NAME
  Legacy: WORKDAY_REST_BASE_URL, WORKDAY_TENANT
"""

import os
from urllib.parse import urljoin

import requests

from workday_extend_url import get_hacker_collection_url


def get_rest_config() -> dict[str, str]:
    """Return REST base URL and tenant from environment.
    Prefers Extend URL (apps/APP_NAME/v1/COLLECTION) when set; else legacy WORKDAY_REST_BASE_URL + tenant.
    """
    extend_base = get_hacker_collection_url()
    if extend_base:
        return {"base_url": extend_base, "tenant": "", "use_extend": True}
    base = (os.environ.get("WORKDAY_REST_BASE_URL") or "").strip().rstrip("/")
    tenant = (os.environ.get("WORKDAY_TENANT") or "").strip()
    return {"base_url": base, "tenant": tenant, "use_extend": False}


def rest_request(
    method: str,
    path_segments: list[str],
    access_token: str,
    *,
    json_body: dict | None = None,
    timeout: int = 30,
) -> dict:
    """
    Perform an authenticated REST request to the Workday API.

    path_segments: URL path parts (no leading/trailing slashes), e.g. ["staffing", "v7", "hack116_wcpdev1", "workers", worker_id].
    access_token: Bearer token from workday_auth.get_workday_bearer_token().
    """
    config = get_rest_config()
    base = config["base_url"]
    if not base:
        raise ValueError(
            "Workday REST base URL is not set. Set WORKDAY_EXTEND_BASE_URL, WORKDAY_APP_NAME, and "
            "WORKDAY_HACKER_COLLECTION_NAME, or WORKDAY_REST_BASE_URL in .env."
        )
    path = "/".join(str(s).strip("/") for s in path_segments if str(s))
    url = urljoin(base + "/", path)
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    if json_body is not None:
        headers["Content-Type"] = "application/json"
    response = requests.request(
        method,
        url,
        json=json_body,
        headers=headers,
        timeout=timeout,
    )
    if not response.ok:
        raise ValueError(
            f"Workday REST error: {response.status_code} {response.reason}. "
            f"Details: {response.text[:1000]}"
        )
    return response.json() if response.content else {}


# --- Operation builders: add new API operations here ---

def get_worker(worker_id: str, access_token: str) -> dict:
    """
    GET a single worker by ID (WID or employee ID).

    Extend: GET {base}/{worker_id}
    Legacy: GET {base}/staffing/v7/{tenant}/workers/{worker_id}
    """
    config = get_rest_config()
    if config.get("use_extend"):
        path_segments = [str(worker_id).strip()]
    else:
        tenant = config["tenant"]
        if not tenant:
            raise ValueError("WORKDAY_TENANT is not set in .env (e.g. hack116_wcpdev1).")
        path_segments = ["staffing", "v7", tenant, "workers", worker_id]
    return rest_request("GET", path_segments, access_token)


