# Workday Build MCP

A **one-stop-shop MCP server** for developing on the Workday Build platform —
Extend apps, AI agents, and orchestrations/integrations. It gives coding agents
(Cursor, Claude Code, etc.) two things:

1. **Graph-backed knowledge** — a queryable knowledge graph built from the
   Workday Extend documentation/forum corpus **and** the reference sample apps,
   so doc/sample lookup is ranked by relationships, not naive grep.
2. **Convention-following scaffolding** — generators that create valid Extend
   apps, PMD pages, business objects, orchestrations, suborchestrations, and AI
   agents following the patterns in the reference apps and the repo skills.

> API discovery is intentionally **out of scope** — a separate MCP handles
> finding Workday APIs. This MCP focuses on building fast.

---

## Architecture

```
                 ┌─────────────────────────────────────────────┐
                 │              workday-build MCP               │
                 │                (FastMCP, stdio)              │
                 └───────────────┬──────────────┬──────────────┘
                                 │              │
              knowledge tools ◄──┘              └──► scaffolding tools
                     │                                   │
        ┌────────────▼────────────┐          ┌───────────▼────────────┐
        │  graph/query.py (BFS    │          │  generators/*.py        │
        │  scored traversal)      │          │  (Extend/PMD/BO/orch/    │
        └────────────▲────────────┘          │   suborch/agent)         │
                     │                        └──────────────────────────┘
        ┌────────────┴───────────────────────────────┐
        │      graphify-out/graph.json (node-link)    │
        │  Graphify-compatible → also servable by     │
        │  `graphify-mcp`                             │
        └────────────▲───────────────┬────────────────┘
                     │               │
        ┌────────────┴───┐   ┌───────┴─────────────────┐
        │ wd_extract.py  │   │ doc_extract.py          │
        │ reference/*    │   │ Documentation/*.md      │
        │ (.pmd .amd .smd│   │ (+ optional Graphify    │
        │  .orchestration│   │  CLI enrichment)        │
        │  .script .agent│   └─────────────────────────┘
        │  .businessobject…)                            
        └────────────────┘
```

### How Graphify is used

Graphify (`graphifyy` on PyPI, CLI `graphify`) turns codebases + docs into a
NetworkX `graph.json` and can serve it over MCP. This project:

- **Emits the same node-link `graph.json` schema** Graphify uses, so the graph
  can also be served directly by `graphify-mcp` if you prefer its query tools.
- **Ships custom Workday extractors** (`graph/wd_extract.py`) because Graphify
  has no extractor for Workday's custom file types (`.pmd`, `.amd`, `.smd`,
  `.orchestration`, `.suborchestration`, `.script`, `.agent`, …). These parse
  the artifacts into a rich domain graph (pages → widgets/endpoints, BOs →
  fields, orchestrations → steps/subflows, agents → skills/tools).
- **Optionally enriches** the markdown docs via the Graphify CLI when it's
  installed (`graph/doc_extract.py::graphify_enrich`). This is best-effort and
  **not required** — the custom builder produces a working graph on its own.

> On Python 3.14, `graphifyy`'s heavy tree-sitter dependency set may not resolve
> cleanly. The custom builder is the default and needs only `mcp`. To enable
> enrichment: `pip install graphifyy` (ideally on Python 3.10–3.12) and rebuild
> with `use_graphify=True`.

---

## Tools (14 — kept ≤ 15)

| Tool | One-liner |
|------|-----------|
| `get_started` | Overview, graph status, and recommended workflow. Call first. |
| `look_up_documentation` | Graph-ranked search of the Workday Extend docs/forum corpus. |
| `search_samples` | Structure-aware search of reference apps (pages, widgets, endpoints, BOs, orch steps, agents) with neighbor context. |
| `find_pattern` | Jump to the canonical reference file(s) for a named pattern (fuzzy-matched). |
| `get_reference_file` | Read the full contents of a reference artifact (sandboxed to `reference/`). |
| `create_workday_extend_app` | Scaffold an Extend app: manifest + `.smd` + `.amd` + `home.pmd`. |
| `add_pmd_page` | Add a PMD page (view/edit/list/create), CRUD-wired to a business object. |
| `create_business_object` | Create a BO + report + view/create tasks + security domain. |
| `create_orchestration` | Scaffold a sync/async/BP/home-card/integration orchestration + global error handler. |
| `create_suborchestration` | Scaffold a reusable sub-flow with input/output vars + local error handler. |
| `create_agent` | Scaffold `.agent` + `.agentskill` + reusable display-image A2UI page. |
| `validate_app` | Static structure/JSON/task-page checks; emits the `wdcli` command. |
| `rebuild_graph` | (Re)index reference samples + docs into the knowledge graph (+ refresh the viz). |
| `visualize_graph` | Generate/refresh the navigable HTML graph view; returns the path to open. |

---

## Graph visualization

Every graph build also writes a self-contained, navigable HTML view to
`graphify-out/graph.html`. It renders the **architecture graph** — apps, PMD
pages, widgets, endpoints, business objects + fields, orchestrations/sub-flows,
agents/skills, and doc topics — using [vis-network](https://visjs.org/) (loaded
from CDN). The ~10k documentation *section* nodes are aggregated out so the view
stays navigable (~870 nodes).

Features: search box, click a legend row to isolate a node kind, hover for
source file + excerpt, physics toggle, fit/zoom/pan.

```bash
# Rebuild the graph (also regenerates graph.html):
python -m workday_build_mcp.graph
# Or, from an MCP client, call the tool:
#   visualize_graph   ->  returns the file path to open
open graphify-out/graph.html          # macOS
# xdg-open graphify-out/graph.html    # Linux
```

> Prefer Graphify's native visuals? Because `graph.json` is Graphify-compatible,
> you can also run `graphify export` / serve it with `graphify-mcp` to get
> Graphify's Obsidian vault, `graph.html`, and `GRAPH_REPORT.md` outputs.

---

## Install & run

```bash
cd workday-build-mcp
python3 -m venv .venv && . .venv/bin/activate
pip install -e .            # installs `mcp`
# Optional Graphify enrichment (best on Python 3.10–3.12):
# pip install -e ".[graphify]"

# Build the knowledge graph (reference samples + docs):
python -m workday_build_mcp.graph            # or: workday-build-graph
# skip Graphify enrichment:
python -m workday_build_mcp.graph --no-graphify
```

### Enable in Cursor

Add to `~/.cursor/mcp.json` (or the project `.cursor/mcp.json`). See
[`mcp.json.example`](./mcp.json.example):

```json
{
  "mcpServers": {
    "workday-build": {
      "command": "/absolute/path/to/workday-build-mcp/.venv/bin/python",
      "args": ["-m", "workday_build_mcp.server"],
      "env": {
        "WORKDAY_BUILD_REPO": "/absolute/path/to/workdayBuildAgent",
        "WORKDAY_BUILD_DOCS": "/Users/you/Desktop/Documentation and Forum Content",
        "WORKDAY_BUILD_OUTPUT": "/absolute/path/to/where/apps/are/created"
      }
    }
  }
}
```

---

## Configuration (env vars)

| Var | Default | Purpose |
|-----|---------|---------|
| `WORKDAY_BUILD_REPO` | parent of this package | Monorepo root. |
| `WORKDAY_BUILD_REFERENCE` | `$REPO/reference` | Reference sample apps to index + scaffold from. |
| `WORKDAY_BUILD_DOCS` | `~/Desktop/Documentation and Forum Content` | Markdown docs/forum corpus. |
| `WORKDAY_BUILD_GRAPH_DIR` | `./graphify-out` | Where `graph.json` is written/read. |
| `WORKDAY_BUILD_OUTPUT` | `$REPO` | Where scaffolding tools create apps. |

---

## Layout

```
workday-build-mcp/
├── pyproject.toml
├── mcp.json.example
├── README.md
├── graphify-out/
│   ├── graph.json                   # generated knowledge graph (committed)
│   ├── graph.html                   # navigable visualization (committed)
│   └── GRAPH_REPORT.md              # node/edge/kind summary
└── src/workday_build_mcp/
    ├── server.py                    # FastMCP server + 14 tools
    ├── config.py                    # env-driven path resolution
    ├── patterns.py                  # curated pattern → reference-file catalog
    ├── validate.py                  # static app validation
    ├── graph/
    │   ├── schema.py                # Graphify-compatible node-link graph
    │   ├── wd_extract.py            # Workday artifact extractors
    │   ├── doc_extract.py           # markdown docs + optional Graphify enrichment
    │   ├── build.py                 # merge → graph.json + GRAPH_REPORT.md
    │   ├── query.py                 # BFS scored query engine
    │   ├── viz.py                    # HTML graph visualization generator
    │   └── __main__.py              # `python -m workday_build_mcp.graph`
    └── generators/                  # scaffolding generators
        ├── extend_app.py  pmd_page.py  business_object.py
        ├── orchestration.py  agent.py  common.py
```
