"""Scaffold a PMD page (view / edit / list / create) into an existing app."""
from __future__ import annotations

from pathlib import Path

from .common import app_root, camel, write_json, result


def _collection(bo: str) -> str:
    return camel(bo) + "s"


def add_pmd_page(app: str, page_id: str, page_type: str = "view",
                 business_object: str | None = None,
                 security_domains: list[str] | None = None) -> str:
    app_dir = app_root(app)
    pres = app_dir / "presentation"
    if not pres.exists():
        pres = app_dir  # allow pointing directly at a presentation dir
    created: list[str] = []
    pt = page_type.lower()
    sd = security_domains or ([f"Manage{business_object}"] if business_object else [])
    coll = _collection(business_object) if business_object else "items"
    var = camel(business_object) if business_object else "item"

    page: dict = {"id": page_id}
    if sd:
        page["securityDomains"] = sd

    if pt == "list":
        page.update({
            "endPoints": [{"name": coll, "baseUrlType": "app", "url": coll,
                           "isCollection": "true", "authType": "sso"}],
            "presentation": {
                "pageType": "VIEW",
                "title": {"type": "title", "label": page_id},
                "body": {"type": "section", "children": [
                    {"type": "grid", "id": f"{var}Grid",
                     "rows": f"<% {coll}.data %>", "rowVariableName": var,
                     "columns": [
                         {"type": "column", "columnId": "name", "label": "Name",
                          "cellTemplate": {"type": "text", "value": f"<% {var}.descriptor %>"}}
                     ]}
                ]},
            },
        })
    elif pt == "create":
        page.update({
            "endPoints": [{"name": "worker", "baseUrlType": "workday-staffing",
                           "url": "workers/me", "authType": "sso"}],
            "outboundData": {
                "outboundEndPoints": [{
                    "name": var, "baseUrlType": "app", "url": coll,
                    "httpMethod": "POST", "authType": "sso",
                    "onSend": "<% self.data.put('createdBy', {'id': worker.id}); return self.data; %>",
                }],
                "responseErrorDetail": {"errorSummary": "<% error %>",
                                        "errors": "<% errors.map(item => { item.error }); %>"},
            },
            "presentation": {
                "pageType": "edit",
                "title": {"type": "title", "label": f"Add {business_object or page_id}"},
                "body": {"type": "section", "children": [
                    {"type": "text", "id": "name", "label": "Name", "required": True,
                     "valueOutBinding": f"{var}.name"}
                ]},
            },
        })
    elif pt == "edit":
        page.update({
            "endPoints": [{"name": var, "baseUrlType": "app",
                           "url": f"<% '{coll}/' + queryParams.{var}Id %>", "authType": "sso"}],
            "outboundData": {"outboundEndPoints": [{
                "name": f"update{var}", "baseUrlType": "app",
                "url": f"<% '{coll}/' + {var}.id %>", "httpMethod": "PUT", "authType": "sso"}]},
            "presentation": {
                "pageType": "edit",
                "title": {"type": "title", "label": f"<% 'Edit - ' + {var}.descriptor %>"},
                "body": {"type": "section", "children": [
                    {"type": "text", "id": "name", "label": "Name",
                     "value": f"<% {var}.name %>", "valueOutBinding": f"update{var}.name"}
                ]},
            },
        })
    else:  # view
        page.update({
            "endPoints": [{"name": var, "baseUrlType": "app",
                           "url": f"<% '{coll}/' + queryParams.{var}Id %>", "authType": "sso"}]
            if business_object else [],
            "presentation": {
                "pageType": "VIEW",
                "title": {"type": "title",
                          "label": f"<% {var}.descriptor %>" if business_object else page_id},
                "body": {"type": "section", "children": [
                    {"type": "text", "label": "Name",
                     "value": f"<% {var}.descriptor %>" if business_object else "", "enabled": False}
                ]},
            },
        })

    write_json(pres / f"{page_id}.pmd", page, created)
    notes = [
        f"Register in the .amd: add a task {{'id':'{page_id}','routingPattern':'/{page_id}','page':{{'id':'{page_id}'}}}}",
    ]
    return result(created, notes)
