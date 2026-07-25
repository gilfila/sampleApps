"""Runtime configuration and path resolution for the Workday Build MCP.

All paths are resolvable via environment variables so the server works both
inside this monorepo and when the package is checked out standalone.
"""
from __future__ import annotations

import os
from pathlib import Path


def _env_path(name: str, default: Path) -> Path:
    val = os.environ.get(name)
    return Path(val).expanduser().resolve() if val else default


# The installed package directory: .../workday-build-mcp/src/workday_build_mcp
PACKAGE_DIR = Path(__file__).resolve().parent
# .../workday-build-mcp
PROJECT_DIR = PACKAGE_DIR.parent.parent
# The monorepo root (parent of workday-build-mcp). When the package is checked
# out standalone this simply resolves to the package's own parent.
REPO_ROOT = _env_path("WORKDAY_BUILD_REPO", PROJECT_DIR.parent)

# Reference sample apps that we graphify + scaffold from.
REFERENCE_DIR = _env_path("WORKDAY_BUILD_REFERENCE", REPO_ROOT / "reference")

# Local Workday Extend documentation / forum corpus (markdown).
DOCS_DIR = _env_path(
    "WORKDAY_BUILD_DOCS",
    Path.home() / "Desktop" / "Documentation and Forum Content",
)

# Where the knowledge graph is written / read.
GRAPH_OUT_DIR = _env_path("WORKDAY_BUILD_GRAPH_DIR", PROJECT_DIR / "graphify-out")
GRAPH_JSON = GRAPH_OUT_DIR / "graph.json"
GRAPH_REPORT = GRAPH_OUT_DIR / "GRAPH_REPORT.md"

# Where scaffolding tools create new apps by default.
OUTPUT_DIR = _env_path("WORKDAY_BUILD_OUTPUT", REPO_ROOT)


def as_dict() -> dict:
    return {
        "repo_root": str(REPO_ROOT),
        "reference_dir": str(REFERENCE_DIR),
        "docs_dir": str(DOCS_DIR),
        "graph_json": str(GRAPH_JSON),
        "output_dir": str(OUTPUT_DIR),
        "reference_exists": REFERENCE_DIR.exists(),
        "docs_exists": DOCS_DIR.exists(),
        "graph_exists": GRAPH_JSON.exists(),
    }
