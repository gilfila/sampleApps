"""
Workday OAuth 2.0 token helper.

Primary flow: use a non-expiring refresh token to retrieve an access token.
Set WORKDAY_REFRESH_TOKEN_NONEXPIRE in .env (from Workday or from a one-time code exchange).
The server calls the token endpoint with grant_type=refresh_token to get an access token.

Fallback: client credentials (WORKDAY_CLIENT_ID, WORKDAY_CLIENT_SECRET, WORKDAY_TOKEN_URL).
"""

import base64
import hashlib
import os
import secrets
from urllib.parse import urlencode

import requests

# Workday API Gateway token endpoint (authorization code / refresh token grants)
WORKDAY_AUTH_TOKEN_URL = "https://auth.api.workday.com/v1/token"


def _load_env() -> dict[str, str]:
    """Load Workday-related vars from environment (after dotenv is loaded)."""
    # Non-expiring refresh token: used to retrieve an access token from the token endpoint
    refresh = (
        os.environ.get("WORKDAY_REFRESH_TOKEN_NONEXPIRE", "").strip()
        or os.environ.get("WORKDAY_REFRESH_TOKEN", "").strip()
    )
    return {
        "client_id": os.environ.get("WORKDAY_CLIENT_ID", "").strip(),
        "client_secret": os.environ.get("WORKDAY_CLIENT_SECRET", "").strip(),
        "token_url": os.environ.get("WORKDAY_TOKEN_URL", "").strip(),
        "api_base_url": os.environ.get("WORKDAY_API_BASE_URL", "").strip(),
        "refresh_token": refresh,
        "redirect_uri": os.environ.get("WORKDAY_REDIRECT_URI", "").strip(),
    }


def _basic_auth_header(client_id: str, client_secret: str) -> str:
    """Build Authorization: Basic base64(client_id:client_secret). Username=client_id, password=client_secret."""
    raw = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(raw.encode()).decode()
    return f"Basic {encoded}"


def _id_header_value(client_id: str, client_secret: str) -> str:
    """Build Authorization: ID base64(client_id:client_secret) per Workday API Gateway."""
    raw = f"{client_id}:{client_secret}"
    return base64.b64encode(raw.encode()).decode()


def generate_code_verifier() -> str:
    """Generate a PKCE code verifier (43–128 chars, alphanumeric + -._~)."""
    return secrets.token_urlsafe(32)


def generate_code_challenge(verifier: str) -> str:
    """Generate PKCE code challenge: base64url(SHA256(verifier)). Method S256."""
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def get_workday_bearer_token(force_refresh: bool = False) -> str:
    """
    Retrieve an access token for Workday using the non-expiring refresh token.

    If WORKDAY_REFRESH_TOKEN_NONEXPIRE (or WORKDAY_REFRESH_TOKEN) is set, calls the
    token endpoint with grant_type=refresh_token to obtain an access token.
    Otherwise falls back to client credentials.

    Raises:
        ValueError: If required config is missing or the token request fails.
    """
    env = _load_env()

    # Use non-expiring refresh token to retrieve an access token (Basic auth: client_id=username, client_secret=password)
    if env["refresh_token"] and env["client_id"] and env["client_secret"]:
        token_url = env["token_url"] or WORKDAY_AUTH_TOKEN_URL
        body = {
            "grant_type": "refresh_token",
            "client_id": env["client_id"],
            "refresh_token": env["refresh_token"],
        }
        if env["redirect_uri"]:
            body["redirect_uri"] = env["redirect_uri"]
        response = requests.post(
            token_url,
            data=body,
            headers={
                "Authorization": _basic_auth_header(env["client_id"], env["client_secret"]),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=30,
        )
        if not response.ok:
            raise ValueError(
                f"Workday token request failed: {response.status_code} "
                f"{response.reason}. Body: {response.text[:500]}"
            )
        data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            raise ValueError(
                "Workday token response did not include access_token. "
                f"Response: {data}"
            )
        return access_token

    # Client credentials (tenant token endpoint)
    if not env["client_id"] or not env["client_secret"] or not env["token_url"]:
        raise ValueError(
            "Missing Workday OAuth config. Set WORKDAY_REFRESH_TOKEN_NONEXPIRE with "
            "WORKDAY_CLIENT_ID and WORKDAY_CLIENT_SECRET (and WORKDAY_TOKEN_URL for API Gateway), "
            "or set WORKDAY_CLIENT_ID, WORKDAY_CLIENT_SECRET, and WORKDAY_TOKEN_URL for client credentials."
        )
    token_data = {
        "grant_type": "client_credentials",
        "client_id": env["client_id"],
        "client_secret": env["client_secret"],
    }
    response = requests.post(
        env["token_url"],
        data=token_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if not response.ok:
        raise ValueError(
            f"Workday token request failed: {response.status_code} "
            f"{response.reason}. Body: {response.text[:500]}"
        )
    data = response.json()
    access_token = data.get("access_token")
    if not access_token:
        raise ValueError(
            "Workday token response did not include access_token. "
            f"Response: {data}"
        )
    return access_token


def get_workday_api_base_url() -> str:
    """Return WORKDAY_API_BASE_URL from environment (base prior to /staffing, no trailing slash)."""
    base = os.environ.get("WORKDAY_API_BASE_URL", "").strip().rstrip("/")
    if not base:
        raise ValueError(
            "WORKDAY_API_BASE_URL is not set in .env."
        )
    return base


def get_workday_authorize_url(state: str = "xyz", response_type: str = "code") -> str:
    """
    Build the authorization request URL (authorization code flow, no PKCE).

    User signs in, then is redirected with code=... in the URL. Exchange the code
    with exchange_authorization_code() and store the returned refresh_token as
    WORKDAY_REFRESH_TOKEN in .env.
    """
    env = _load_env()
    if not env["client_id"]:
        raise ValueError("WORKDAY_CLIENT_ID is required to build the authorize URL.")
    params = {
        "response_type": response_type,
        "client_id": env["client_id"],
        "state": state,
    }
    if env["redirect_uri"]:
        params["redirect_uri"] = env["redirect_uri"]
    base = "https://auth.api.workday.com/v1/authorize"
    return f"{base}?{urlencode(params)}"


def get_workday_authorize_url_pkce(
    state: str = "xyz",
    redirect_uri_override: str | None = None,
) -> tuple[str, str]:
    """
    Build the authorization request URL with PKCE (recommended).

    Returns (authorize_url, code_verifier). Save the code_verifier and pass it to
    exchange_authorization_code(code, code_verifier=...) when exchanging the code.
    The code_challenge is base64url(SHA256(code_verifier)); method S256.

    If redirect_uri_override is set, use it instead of WORKDAY_REDIRECT_URI (e.g. for local callback server).
    """
    env = _load_env()
    if not env["client_id"]:
        raise ValueError("WORKDAY_CLIENT_ID is required to build the authorize URL.")
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    params = {
        "response_type": "code",
        "client_id": env["client_id"],
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    uri = redirect_uri_override or env["redirect_uri"]
    if uri:
        params["redirect_uri"] = uri
    base = "https://auth.api.workday.com/v1/authorize"
    url = f"{base}?{urlencode(params)}"
    return url, verifier


def exchange_authorization_code(
    code: str,
    redirect_uri: str | None = None,
    token_url: str | None = None,
    code_verifier: str | None = None,
) -> dict:
    """
    Exchange an authorization code for access_token and refresh_token.

    Call this once after the user is redirected with code=... from the authorize URL.
    Use the returned refresh_token as WORKDAY_REFRESH_TOKEN in .env.

    For PKCE: pass the code_verifier that was used to generate the code_challenge
    in the authorize request. The server validates it and returns tokens.
    """
    env = _load_env()
    if not env["client_id"] or not env["client_secret"]:
        raise ValueError("WORKDAY_CLIENT_ID and WORKDAY_CLIENT_SECRET are required.")
    uri = redirect_uri or env["redirect_uri"]
    if not uri:
        raise ValueError("redirect_uri is required (pass it or set WORKDAY_REDIRECT_URI).")
    url = token_url or env["token_url"] or WORKDAY_AUTH_TOKEN_URL
    auth_header = f"ID {_id_header_value(env['client_id'], env['client_secret'])}"
    body = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": env["client_id"],
        "redirect_uri": uri,
    }
    if code_verifier:
        body["code_verifier"] = code_verifier
    response = requests.post(
        url,
        data=body,
        headers={
            "Authorization": auth_header,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=30,
    )
    if not response.ok:
        raise ValueError(
            f"Token exchange failed: {response.status_code} {response.reason}. "
            f"Body: {response.text[:500]}"
        )
    return response.json()
