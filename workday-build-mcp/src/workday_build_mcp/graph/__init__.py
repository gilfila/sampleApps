"""Knowledge-graph subsystem for the Workday Build MCP.

Import the submodules directly to avoid shadowing the ``query`` module with the
``query`` function, e.g. ``from .graph import query as gquery``.
"""
from .build import build_graph

__all__ = ["build_graph"]
