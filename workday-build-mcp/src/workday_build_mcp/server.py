"""Workday Build MCP server.

A one-stop-shop MCP for developing on the Workday Build platform (Extend apps,
AI agents, and orchestrations/integrations). Combines:

  * a graph-backed knowledge base of Workday docs + reference samples
    (look_up_documentation, search_samples, find_pattern, get_reference_file)
  * convention-following scaffolding generators
    (create_workday_extend_app, add_pmd_page, create_business_object,
     create_orchestration, create_suborchestration, create_agent)
  * static validation + graph rebuild (validate_app, rebuild_graph)

Tool count is intentionally kept <= 15. API discovery is delegated to a
separate MCP by design.
"""
from __future__ import annotations

import difflib
import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from . import config
from .graph import query as gquery
from .graph.build import build_graph
from .patterns import PATTERNS
from .validate import validate_app as _validate_app
from .generators import (
    create_extend_app as _create_extend_app,
    add_pmd_page as _add_pmd_page,
    create_business_object as _create_business_object,
    create_orchestration as _create_orchestration,
    create_suborchestration as _create_suborchestration,
    create_agent as _create_agent,
)

mcp = FastMCP("workday-build")


# --------------------------------------------------------------------------- #
# Orientation
# --------------------------------------------------------------------------- #
@mcp.tool()
def get_started() -> str:
    """Start here. Returns what this MCP can do, the current knowledge-graph
    status, and the recommended workflow for building Workday apps, agents,
    and orchestrations. Call this first in a new session."""
    cfg = config.as_dict()
    idx = gquery.load_index()
    graph_line = (
        f"{len(idx.nodes)} nodes indexed" if idx else
        "NOT BUILT — run rebuild_graph first"
    )
    return f"""Workday Build MCP — one-stop shop for the Workday Build platform.

KNOWLEDGE (graph-backed, not grep):
  • look_up_documentation(query)  — search Workday Extend docs + forum corpus
  • search_samples(query)         — search reference sample apps by structure
  • find_pattern(pattern)         — jump to the canonical reference file(s)
  • get_reference_file(path)      — read a full reference artifact

SCAFFOLDING (follows repo + skill conventions):
  • create_workday_extend_app(name, ...)   — manifest + smd + amd + home page
  • add_pmd_page(app, page_id, page_type)  — view/edit/list/create page
  • create_business_object(app, name, ...) — BO + report + tasks + security domain
  • create_orchestration(app, name, type)  — sync/async/BP orchestration
  • create_suborchestration(app, name, ...) — reusable sub-flow + error handler
  • create_agent(app, name, ...)           — .agent + .agentskill + A2UI page

OPS:
  • validate_app(app)   — static structure/JSON checks + wdcli command
  • rebuild_graph()     — (re)index reference samples + docs into the graph

STATUS:
  graph: {graph_line}
  reference: {cfg['reference_dir']} (exists={cfg['reference_exists']})
  docs:      {cfg['docs_dir']} (exists={cfg['docs_exists']})
  output:    {cfg['output_dir']}

TYPICAL FLOW:
  1) look_up_documentation / find_pattern to learn the pattern
  2) create_* to scaffold, add_pmd_page to add screens
  3) validate_app, then `wdcli app validate/upload` outside this MCP.

Note: Workday API discovery is handled by a separate MCP — not here."""


# --------------------------------------------------------------------------- #
# Knowledge tools
# --------------------------------------------------------------------------- #
@mcp.tool()
def look_up_documentation(query: str, top_k: int = 8) -> str:
    """Search the local Workday Extend documentation + forum corpus for best
    practices, syntax, and guidance. Graph-ranked; returns doc sections with
    the source file and line so you can cite/open them."""
    return gquery.query(query, kinds={"doc_section", "doc_topic", "doc_file"},
                        top_k=top_k, with_neighbors=False)


@mcp.tool()
def search_samples(query: str, top_k: int = 8) -> str:
    """Search the reference sample apps by structure (pages, widgets, endpoints,
    business objects, orchestration steps, agents). Graph-ranked and enriched
    with each result's neighbors (e.g. the endpoints a page uses)."""
    sample_kinds = {
        "pmd_page", "app_metadata", "site_metadata", "card", "pod", "script",
        "business_object", "bo_field", "task", "report", "security_domain",
        "attachment", "business_process", "orchestration", "suborchestration",
        "orch_step", "agent", "agent_skill", "widget_type", "endpoint",
        "outbound_endpoint", "script_function", "flow", "data_provider", "app",
    }
    return gquery.query(query, kinds=sample_kinds, top_k=top_k, with_neighbors=True)


@mcp.tool()
def find_pattern(pattern: str) -> str:
    """Given a pattern name (e.g. 'editable grid', 'suborchestration error
    handling', 'business process', 'a2ui'), return the canonical reference
    file(s) that demonstrate it. Falls back to graph search when unknown."""
    key = pattern.strip().lower()
    files = PATTERNS.get(key)
    if not files:
        # fuzzy match against known pattern names
        close = difflib.get_close_matches(key, PATTERNS.keys(), n=3, cutoff=0.5)
        if close:
            files = PATTERNS[close[0]]
    if files:
        lines = [f"Pattern '{pattern}' → reference file(s):"]
        for rel in files:
            full = config.REFERENCE_DIR / rel
            marker = "" if full.exists() else "  (not found — run rebuild_graph)"
            lines.append(f"  • {rel}{marker}")
        lines.append("")
        lines.append("Read one with get_reference_file(path=...) to adapt it.")
        return "\n".join(lines)
    # fall back to graph
    return ("No curated pattern matched; graph search results:\n\n"
            + gquery.query(pattern, top_k=6, with_neighbors=True))


@mcp.tool()
def get_reference_file(path: str, max_chars: int = 12000) -> str:
    """Return the full contents of a reference artifact. `path` is relative to
    the reference directory (as returned by search_samples/find_pattern) or an
    absolute path inside it. Use this to read a real example before adapting."""
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = config.REFERENCE_DIR / path
    try:
        p = p.resolve()
        p.relative_to(config.REFERENCE_DIR.resolve())
    except (ValueError, OSError):
        return f"Refused: '{path}' is outside the reference directory."
    if not p.exists() or not p.is_file():
        return f"Not found: {p}"
    text = p.read_text(encoding="utf-8", errors="ignore")
    truncated = len(text) > max_chars
    body = text[:max_chars]
    header = f"# {p.relative_to(config.REFERENCE_DIR.resolve())}\n"
    if truncated:
        body += f"\n\n... (truncated at {max_chars} chars; file is {len(text)} chars)"
    return header + body


# --------------------------------------------------------------------------- #
# Scaffolding tools
# --------------------------------------------------------------------------- #
@mcp.tool()
def create_workday_extend_app(name: str, description: str = "",
                              with_model: bool = False,
                              output_dir: str = "") -> str:
    """Scaffold a new Workday Extend app: appManifest.json, .smd (auth/CDN),
    .amd (tasks/flows/dataProviders), and a home.pmd. Set with_model=True to
    also create a model/ directory for business objects."""
    return _create_extend_app(name, description, with_model, output_dir or None)


@mcp.tool()
def add_pmd_page(app: str, page_id: str, page_type: str = "view",
                 business_object: str = "") -> str:
    """Add a PMD page to an app. page_type is one of view|edit|list|create.
    Provide business_object to wire CRUD endpoints and value bindings. `app` is
    an app directory name (under the output dir) or an absolute path."""
    return _add_pmd_page(app, page_id, page_type, business_object or None)


@mcp.tool()
def create_business_object(app: str, name: str, fields_json: str = "",
                           with_report: bool = True, with_tasks: bool = True) -> str:
    """Create a business object plus (optionally) a report, view/create tasks,
    and a security domain. fields_json is a JSON array like
    '[{"name":"breed","type":"TEXT","label":"Breed"},{"name":"owner","type":"SINGLE_INSTANCE","target":"WORKER"}]'.
    Types: TEXT, INTEGER, BOOLEAN, DATE, SINGLE_INSTANCE, MULTI_INSTANCE."""
    fields = None
    if fields_json.strip():
        try:
            fields = json.loads(fields_json)
        except json.JSONDecodeError as e:
            return f"Invalid fields_json: {e}"
    return _create_business_object(app, name, fields, with_report, with_tasks, True)


@mcp.tool()
def create_orchestration(app: str, name: str, orch_type: str = "SYNCHRONOUS") -> str:
    """Scaffold an orchestration. orch_type is one of SYNCHRONOUS, ASYNCHRONOUS,
    BUSINESS_PROCESS, HOME_CARD, INTEGRATION_SYSTEM. Includes a global error
    handler; build step bodies in Orchestration Builder."""
    return _create_orchestration(app, name, orch_type)


@mcp.tool()
def create_suborchestration(app: str, name: str, input_variables: str = "",
                            output_variables: str = "",
                            with_error_handling: bool = True) -> str:
    """Scaffold a reusable suborchestration with input/output variables and a
    local error handler (OSK141 pattern). input_variables/output_variables are
    comma-separated names, e.g. 'workerId,effectiveDate'."""
    ins = [s.strip() for s in input_variables.split(",") if s.strip()] or None
    outs = [s.strip() for s in output_variables.split(",") if s.strip()] or None
    return _create_suborchestration(app, name, ins, outs, with_error_handling)


@mcp.tool()
def create_agent(app: str, name: str, description: str = "",
                 skills: str = "", with_a2ui: bool = True) -> str:
    """Scaffold a Workday AI agent: a .agent (system prompt + skills), a main
    .agentskill, and (with_a2ui) a reusable display-image skill + A2UI page.
    `skills` is a comma-separated list of additional skill names."""
    skill_list = [s.strip() for s in skills.split(",") if s.strip()] or None
    return _create_agent(app, name, description, skill_list, with_a2ui)


# --------------------------------------------------------------------------- #
# Ops tools
# --------------------------------------------------------------------------- #
@mcp.tool()
def validate_app(app: str) -> str:
    """Statically validate an app: required files, JSON well-formedness, and
    task→page cross-references. Emits the authoritative `wdcli app validate`
    command to run next. `app` is a directory name or absolute path."""
    return _validate_app(app)


@mcp.tool()
def rebuild_graph(use_graphify: bool = True) -> str:
    """(Re)build the knowledge graph from the reference samples + documentation
    corpus. Run this after adding samples/docs or on first setup. Set
    use_graphify=False to skip optional Graphify CLI enrichment. Also refreshes
    the HTML visualization."""
    stats = build_graph(use_graphify=use_graphify)
    gquery._load.cache_clear()  # drop the cached index so queries see the rebuild
    return "Graph rebuilt:\n" + json.dumps(stats, indent=2)


@mcp.tool()
def visualize_graph() -> str:
    """Generate/refresh a navigable HTML visualization of the knowledge graph
    (architecture view: apps, pages, widgets, endpoints, business objects,
    orchestrations, agents, doc topics). Returns the file path to open in a
    browser plus summary stats."""
    from .graph.viz import build_visualization
    try:
        viz = build_visualization()
    except FileNotFoundError as e:
        return str(e)
    return (
        f"Graph visualization written to:\n  {viz['html']}\n\n"
        f"Open it in a browser (file://{viz['html']}).\n"
        f"Showing {viz['nodes_shown']} nodes / {viz['edges_shown']} edges "
        f"(of {viz['total_nodes']} total; documentation sections are aggregated out).\n"
        f"Node kinds: {', '.join(viz['kinds'])}"
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
