"""Scaffold a Workday Extend application (manifest + smd + amd + home page)."""
from __future__ import annotations

from .common import (app_root, reference_id, hex_id, slug, write_json,
                     write_text, result)


def create_extend_app(name: str, description: str = "", with_model: bool = False,
                       output_dir: str | None = None) -> str:
    ref = reference_id(name)
    app_dir = app_root(output_dir or ref)
    pres = app_dir / "presentation"
    created: list[str] = []

    manifest = {
        "id": hex_id(16),
        "referenceId": ref,
        "name": name,
        "description": description or name,
        "latestVersion": hex_id(16),
    }
    write_json(app_dir / "appManifest.json", manifest, created)

    smd = {
        "siteId": ref,
        "applicationId": ref,
        "authType": "sso",
        "cdnEnabled": False,
        "locales": [{"language": "en", "default": True}],
    }
    write_json(pres / f"{ref}.smd", smd, created)

    amd = {
        "applicationId": ref,
        "appProperties": [{"key": "appName", "value": name}],
        "dataProviders": [
            {"key": "app", "value": "<% apiGatewayEndpoint + '/apps/' + site.applicationId + '/v1/' %>"},
            {"key": "workday-staffing", "value": "<% apiGatewayEndpoint + '/staffing/v7/' %>"},
            {"key": "workday-wql", "value": "<% apiGatewayEndpoint + '/wql/v1/' %>"},
        ],
        "tasks": [{"id": "home", "routingPattern": "/", "page": {"id": "home"}}],
        "flowDefinitions": [
            {"id": "mainFlow", "flowSteps": [
                {"id": "home", "startsFlow": True, "endsFlow": True, "taskId": "home"}
            ]}
        ],
    }
    write_json(pres / f"{ref}.amd", amd, created)

    home = {
        "id": "home",
        "endPoints": [
            {"name": "worker", "baseUrlType": "workday-staffing", "url": "workers/me", "authType": "sso"}
        ],
        "presentation": {
            "pageType": "VIEW",
            "title": {"type": "title", "label": name},
            "body": {"type": "section", "children": [
                {"type": "text", "label": "Welcome", "value": "<% 'Hello ' + worker.descriptor %>", "enabled": False}
            ]},
        },
    }
    write_json(pres / "home.pmd", home, created)

    notes = [
        f"referenceId = {ref}",
        f"Validate:  wdcli app validate {app_dir}",
        f"Upload:    wdcli app upload {app_dir}",
    ]
    if with_model:
        (app_dir / "model").mkdir(parents=True, exist_ok=True)
        write_text(app_dir / "model" / ".gitkeep", "", created)
        notes.append("Model dir created — add business objects with create_business_object.")
    return result(created, notes)
