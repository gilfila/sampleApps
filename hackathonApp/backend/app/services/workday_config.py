"""Workday integration config: in-app (AppSetting) and env vars."""

import os
import copy
import logging

logger = logging.getLogger(__name__)

WORKDAY_CONFIG_KEY = "workday"

# Env var names -> config dict keys
_ENV_TO_KEY = {
    "WORKDAY_TENANT": "tenant",
    "WORKDAY_CLIENT_ID": "client_id",
    "WORKDAY_CLIENT_SECRET": "client_secret",
    "WORKDAY_REFRESH_TOKEN": "refresh_token",
    "WORKDAY_CUSTOM_OBJECT_NAME": "custom_object_name",
    "WORKDAY_TICKET_CUSTOM_OBJECT_NAME": "ticket_custom_object_name",
    "WORKDAY_SYNC_INTERVAL": "sync_interval",
    "WORKDAY_TICKET_SYNC_INTERVAL": "ticket_sync_interval",
    "WORKDAY_TICKET_SYNC_RETRY_ATTEMPTS": "ticket_sync_retry_attempts",
}


def get_workday_config():
    """Return Workday config dict from env and in-app settings (AppSetting). Env is base; in-app overrides."""
    config = {}
    for env_name, key in _ENV_TO_KEY.items():
        val = os.environ.get(env_name)
        if val is not None:
            if key in ("sync_interval", "ticket_sync_interval", "ticket_sync_retry_attempts"):
                try:
                    config[key] = int(val)
                except (TypeError, ValueError):
                    config[key] = val
            else:
                config[key] = val
    try:
        from app.models import AppSetting
        row = AppSetting.query.get(WORKDAY_CONFIG_KEY)
        if row and isinstance(row.value, dict):
            merged = copy.deepcopy(config)
            merged.update(row.value)
            return merged
    except Exception as e:
        logger.debug("Loading Workday config from DB: %s", e)
    return config


def is_workday_configured():
    """True if Workday OAuth credentials are present (tenant, client_id, client_secret, refresh_token)."""
    c = get_workday_config()
    return bool(
        c.get("tenant")
        and c.get("client_id")
        and c.get("client_secret")
        and c.get("refresh_token")
    )


def mask_secrets(config):
    """Return a copy of config with secret values masked for API responses."""
    out = copy.deepcopy(config)
    for key in ("client_secret", "refresh_token"):
        if key in out and out[key]:
            out[key] = "***"
    return out
