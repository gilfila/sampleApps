"""CLI: python -m workday_build_mcp.graph  ->  (re)build the knowledge graph."""
from __future__ import annotations

import argparse
import json

from .build import build_graph


def main() -> None:
    p = argparse.ArgumentParser(description="Build the Workday Build knowledge graph.")
    p.add_argument("--no-graphify", action="store_true", help="Skip optional Graphify CLI enrichment.")
    args = p.parse_args()
    stats = build_graph(use_graphify=not args.no_graphify)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
