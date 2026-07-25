"""Scaffold a business object (+ optional report, tasks, security domain)."""
from __future__ import annotations

from .common import app_root, camel, pascal, write_json, result

_VALID_TYPES = {"TEXT", "INTEGER", "BOOLEAN", "DATE", "SINGLE_INSTANCE", "MULTI_INSTANCE"}


def create_business_object(app: str, name: str, fields: list[dict] | None = None,
                           with_report: bool = True, with_tasks: bool = True,
                           with_security_domain: bool = True) -> str:
    app_dir = app_root(app)
    model = app_dir / "model"
    created: list[str] = []
    bo = pascal(name)
    coll = camel(bo) + "s"
    domain = f"Manage{bo}"

    fields = fields or [{"name": "name", "type": "TEXT", "label": "Name"}]
    bo_fields = []
    for i, f in enumerate(fields, 1):
        ftype = (f.get("type") or "TEXT").upper()
        if ftype not in _VALID_TYPES:
            ftype = "TEXT"
        entry = {"id": i, "name": f["name"], "type": ftype,
                 "label": f.get("label", f["name"].title())}
        if i == 1:
            entry["useForDisplay"] = True
            entry["isReferenceId"] = True
        if ftype == "DATE":
            entry["precision"] = f.get("precision", "DAY")
        if ftype in ("SINGLE_INSTANCE", "MULTI_INSTANCE") and f.get("target"):
            entry["target"] = f["target"]
        bo_fields.append(entry)

    bo_def = {
        "id": 1, "name": bo, "label": bo,
        "defaultSecurityDomains": [domain] if with_security_domain else [],
        "defaultCollection": {"name": coll, "label": f"All {bo}s",
                              "description": f"All {bo} records"},
        "fields": bo_fields,
    }
    write_json(model / f"{bo}.businessobject", bo_def, created)

    if with_security_domain:
        write_json(model / f"{domain}.securitydomain",
                   {"id": 1, "name": domain, "label": f"Manage: {bo}",
                    "enabledForPageSecurity": True}, created)

    if with_report:
        write_json(model / f"All{bo}s.report", {
            "id": 1, "name": f"All{bo}s", "businessObject": bo,
            "defaultSecurityDomains": [domain] if with_security_domain else [],
            "columns": [{"id": i, "name": f["label"], "order": chr(96 + i), "field": f["name"]}
                        for i, f in enumerate(bo_fields, 1)],
        }, created)

    if with_tasks:
        write_json(model / f"View{bo}.task", {
            "id": 2, "name": f"View{bo}", "label": f"View {bo}",
            "routePath": f"/{coll}/{{taskObjectId}}", "businessObject": bo,
            "securityDomains": [domain] if with_security_domain else []}, created)
        write_json(model / f"Create{bo}.task", {
            "id": 3, "name": f"Create{bo}", "label": f"Create {bo}",
            "routePath": f"/{coll}/create",
            "securityDomains": [domain] if with_security_domain else []}, created)

    notes = [
        f"BO '{bo}' collection = '{coll}'  (REST: GET/POST {coll}, GET/PUT/DELETE {coll}/{{id}})",
        f"Scaffold UI:  add_pmd_page with business_object='{bo}' (list/view/create/edit)",
    ]
    return result(created, notes)
