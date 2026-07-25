"""Static validation for Workday Extend apps (structure + JSON well-formedness).

This is a fast local pre-check; the authoritative validator is `wdcli app
validate`, whose command we emit at the end.
"""
from __future__ import annotations

import json
from pathlib import Path

from .generators.common import app_root

_JSON_EXTS = {".pmd", ".amd", ".smd", ".card", ".pod", ".businessobject",
              ".task", ".report", ".securitydomain", ".attachment",
              ".businessprocess", ".orchestration", ".suborchestration",
              ".wqlquery", ".carddefinition", ".json"}


def validate_app(app: str) -> str:
    app_dir = app_root(app)
    if not app_dir.exists():
        return f"App directory not found: {app_dir}"
    errors: list[str] = []
    warnings: list[str] = []
    info: list[str] = []

    manifest = app_dir / "appManifest.json"
    if not manifest.exists():
        errors.append("Missing appManifest.json")
    else:
        try:
            m = json.loads(manifest.read_text(encoding="utf-8"))
            if not m.get("referenceId"):
                errors.append("appManifest.json missing 'referenceId'")
        except Exception as e:
            errors.append(f"appManifest.json invalid JSON: {e}")

    pres = app_dir / "presentation"
    has_orch = (app_dir / "orchestration").exists()
    if pres.exists():
        smds = list(pres.glob("*.smd"))
        amds = list(pres.glob("*.amd"))
        if not smds:
            warnings.append("No .smd (site metadata) in presentation/")
        if not amds:
            warnings.append("No .amd (app metadata) in presentation/")
        if not list(pres.glob("*.pmd")):
            warnings.append("No .pmd pages in presentation/")
    elif not has_orch:
        errors.append("App has neither presentation/ nor orchestration/ directory")

    checked = 0
    for path in app_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in _JSON_EXTS:
            checked += 1
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as e:
                errors.append(f"Invalid JSON: {path.relative_to(app_dir)} — {e}")

    # cross-check: tasks referenced in .amd have matching pages
    for amd in pres.glob("*.amd") if pres.exists() else []:
        try:
            data = json.loads(amd.read_text(encoding="utf-8"))
            page_ids = {p.stem for p in pres.glob("*.pmd")}
            for t in (data.get("tasks") or []):
                pid = (t.get("page") or {}).get("id")
                if pid and pid not in page_ids:
                    warnings.append(f"Task '{t.get('id')}' references missing page '{pid}.pmd'")
        except Exception:
            pass

    info.append(f"Checked {checked} JSON artifact(s).")
    status = "PASS" if not errors else "FAIL"
    lines = [f"Validation: {status}  ({app_dir})", ""]
    if errors:
        lines += ["ERRORS:"] + [f"  ✗ {e}" for e in errors] + [""]
    if warnings:
        lines += ["WARNINGS:"] + [f"  ! {w}" for w in warnings] + [""]
    lines += ["INFO:"] + [f"  · {i}" for i in info]
    lines += ["", f"Run authoritative validation:  wdcli app validate {app_dir}"]
    return "\n".join(lines)
