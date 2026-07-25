"""Build the unified Workday Build knowledge graph.

Merges:
  - the Workday artifact graph (reference sample apps)
  - the documentation graph (local markdown corpus)
  - optional Graphify CLI enrichment over the docs

Writes a Graphify-compatible `graph.json` plus a `GRAPH_REPORT.md` summary.
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import config
from .schema import Graph
from .wd_extract import build_reference_graph
from .doc_extract import build_docs_graph, graphify_enrich
from .link import resolve_cross_references


def build_graph(
    reference_dir: Path | None = None,
    docs_dir: Path | None = None,
    out_json: Path | None = None,
    use_graphify: bool = True,
) -> dict:
    reference_dir = reference_dir or config.REFERENCE_DIR
    docs_dir = docs_dir or config.DOCS_DIR
    out_json = out_json or config.GRAPH_JSON
    out_json.parent.mkdir(parents=True, exist_ok=True)

    g = Graph()
    ref_g = build_reference_graph(reference_dir)
    g.merge(ref_g)
    docs_g = build_docs_graph(docs_dir)
    g.merge(docs_g)

    graphify_used = False
    if use_graphify:
        enriched = graphify_enrich(docs_dir)
        if enriched is not None:
            g.merge(enriched)
            graphify_used = True

    link_counts = resolve_cross_references(g)

    data = g.to_node_link()
    out_json.write_text(json.dumps(data), encoding="utf-8")

    stats = g.stats()
    stats["graphify_enrichment"] = graphify_used
    stats["cross_links"] = link_counts
    stats["reference_dir"] = str(reference_dir)
    stats["docs_dir"] = str(docs_dir)
    stats["graph_json"] = str(out_json)
    _write_report(g, stats, config.GRAPH_REPORT)

    # Best-effort: regenerate the HTML visualization alongside the graph.
    try:
        from .viz import build_visualization
        viz = build_visualization()
        stats["visualization_html"] = viz["html"]
        stats["visualization_nodes"] = viz["nodes_shown"]
    except Exception as exc:  # pragma: no cover - viz is non-critical
        stats["visualization_error"] = str(exc)
    return stats


def _write_report(g: Graph, stats: dict, report_path: Path) -> None:
    lines = [
        "# Workday Build Knowledge Graph — Report",
        "",
        f"- Nodes: **{stats['nodes']}**",
        f"- Edges: **{stats['edges']}**",
        f"- Graphify enrichment: **{stats['graphify_enrichment']}**",
        f"- Reference dir: `{stats['reference_dir']}`",
        f"- Docs dir: `{stats['docs_dir']}`",
        "",
        "## Node kinds",
        "",
        "| Kind | Count |",
        "|------|-------|",
    ]
    for kind, count in stats["kinds"].items():
        lines.append(f"| {kind or '(file)'} | {count} |")
    # apps
    apps = sorted({n["label"] for n in g.nodes.values() if n.get("kind") == "app"})
    lines += ["", "## Reference apps", ""]
    lines += [f"- {a}" for a in apps]
    cross = stats.get("cross_links") or {}
    if cross:
        lines += ["", "## Cross-reference links resolved", ""]
        for k, v in sorted(cross.items()):
            lines.append(f"- {k}: **{v}**")
    report_path.write_text("\n".join(lines), encoding="utf-8")
