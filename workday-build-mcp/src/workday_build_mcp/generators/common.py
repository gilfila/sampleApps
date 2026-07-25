"""Shared helpers for scaffolding generators."""
from __future__ import annotations

import json
import re
import secrets
from pathlib import Path

from .. import config


def slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return s or "app"


def camel(name: str) -> str:
    parts = re.split(r"[^a-zA-Z0-9]+", name)
    parts = [p for p in parts if p]
    if not parts:
        return "item"
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])


def pascal(name: str) -> str:
    parts = [p for p in re.split(r"[^a-zA-Z0-9]+", name) if p]
    return "".join(p.capitalize() for p in parts) or "Item"


def reference_id(base: str) -> str:
    return f"{slug(base)}_{secrets.token_hex(3)}"


def hex_id(n: int = 16) -> str:
    return secrets.token_hex(n)


def app_root(app: str) -> Path:
    """Resolve an app directory. Accepts an absolute path or a name under OUTPUT_DIR."""
    p = Path(app).expanduser()
    if p.is_absolute():
        return p
    return config.OUTPUT_DIR / app


def write_json(path: Path, data: dict, created: list[str], overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        created.append(f"SKIP (exists): {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    created.append(str(path))


def write_text(path: Path, text: str, created: list[str], overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        created.append(f"SKIP (exists): {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    created.append(str(path))


def result(created: list[str], notes: list[str] | None = None) -> str:
    lines = ["Created / updated files:"]
    lines += [f"  - {c}" for c in created]
    if notes:
        lines += ["", "Notes:"]
        lines += [f"  - {n}" for n in notes]
    return "\n".join(lines)
