"""Generate a navigable HTML visualization of the knowledge graph.

The full graph is dominated by ~10k documentation-section nodes, which are not
useful to render. This builds a *reduced architecture graph* — apps, pages,
widgets, endpoints, business objects, orchestrations, agents, and doc topics —
and emits a self-contained HTML page (vis-network via CDN) with search,
kind-based coloring, a legend, and physics controls.

By default we also hide high-cardinality *leaf* kinds (script functions, BO
fields, individual orch steps) so the view shows how things connect rather than
a star of dangling children.
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import config

# Kinds excluded from the visualization (too numerous / low-signal to render).
_EXCLUDE_KINDS = {
    "doc_section",
    # Leaf clutter — still in graph.json for search; omit from architecture viz.
    "bo_field",
    "script_function",
    "orch_step",
    "json_config",
}

# Color per node kind (grouped by concern).
_COLORS = {
    "platform": "#ffffff",
    "app": "#1f77b4",
    "pmd_page": "#2ca02c",
    "widget_type": "#98df8a",
    "endpoint": "#ff7f0e",
    "outbound_endpoint": "#ffbb78",
    "base_url": "#d62728",
    "data_provider": "#ff9896",
    "business_object": "#9467bd",
    "bo_field": "#c5b0d5",
    "bo_ref": "#c5b0d5",
    "task": "#8c564b",
    "task_ref": "#c49c94",
    "report": "#e377c2",
    "security_domain": "#7f7f7f",
    "attachment": "#bcbd22",
    "business_process": "#17becf",
    "orchestration": "#393b79",
    "suborchestration": "#5254a3",
    "orch_step": "#6b6ecf",
    "subflow_ref": "#9c9ede",
    "script": "#637939",
    "script_function": "#8ca252",
    "endpoint_invoke": "#b5cf6b",
    "flow": "#843c39",
    "card": "#ad494a",
    "card_definition": "#d6616b",
    "pod": "#e7969c",
    "agent": "#7b4173",
    "agent_skill": "#a55194",
    "skill_ref": "#ce6dbd",
    "agent_tool": "#de9ed6",
    "wql_query": "#3182bd",
    "doc_topic": "#31a354",
    "doc_file": "#a1d99b",
    "site_metadata": "#636363",
    "app_metadata": "#969696",
    "json_config": "#bdbdbd",
}
_DEFAULT_COLOR = "#cccccc"

# Prefer these kinds when over the node cap (architecture spine).
_PRIORITY_KINDS = {
    "platform", "app", "doc_topic", "pmd_page", "business_object",
    "orchestration", "suborchestration", "agent", "agent_skill",
    "task", "endpoint", "widget_type", "flow", "card", "pod",
}


def build_visualization(out_html: Path | None = None, max_nodes: int = 1200) -> dict:
    out_html = out_html or (config.GRAPH_OUT_DIR / "graph.html")
    if not config.GRAPH_JSON.exists():
        raise FileNotFoundError(
            f"{config.GRAPH_JSON} not found — build the graph first (rebuild_graph)."
        )
    data = json.loads(config.GRAPH_JSON.read_text(encoding="utf-8"))
    all_nodes = {n["id"]: n for n in data.get("nodes", [])}
    all_edges = data.get("links") or data.get("edges") or []

    kept = {
        nid: n for nid, n in all_nodes.items()
        if n.get("kind") not in _EXCLUDE_KINDS
    }

    # Degree within the kept set (used for sizing + optional pruning).
    deg: dict[str, int] = {nid: 0 for nid in kept}
    for e in all_edges:
        s, t = e.get("source"), e.get("target")
        if s in deg and t in deg:
            deg[s] += 1
            deg[t] += 1

    if len(kept) > max_nodes:
        def score(nid: str) -> tuple:
            kind = kept[nid].get("kind", "")
            pri = 0 if kind in _PRIORITY_KINDS else 1
            return (pri, -deg.get(nid, 0))
        keep_ids = set(sorted(kept, key=score)[:max_nodes])
        kept = {nid: n for nid, n in kept.items() if nid in keep_ids}
        deg = {nid: 0 for nid in kept}
        for e in all_edges:
            s, t = e.get("source"), e.get("target")
            if s in deg and t in deg:
                deg[s] += 1
                deg[t] += 1

    # Drop nodes that became isolated after pruning (true viz orphans).
    kept = {nid: n for nid, n in kept.items() if deg.get(nid, 0) > 0 or n.get("kind") == "platform"}

    # Assign community levels for hierarchical layout (platform → app → rest).
    community_index: dict[str, int] = {}
    for n in kept.values():
        c = n.get("community_name") or n.get("kind") or "other"
        if c not in community_index:
            community_index[c] = len(community_index)

    vnodes = []
    for nid, n in kept.items():
        kind = n.get("kind", "")
        label = n.get("label", nid)
        title = f"{kind}: {label}"
        if n.get("source_file"):
            title += f"\n{n['source_file']}"
        if n.get("text"):
            title += f"\n{n['text'][:200]}"
        level = 0 if kind == "platform" else (1 if kind in ("app", "doc_topic") else 2)
        vnodes.append({
            "id": nid,
            "label": label if len(label) <= 28 else label[:27] + "…",
            "title": title,
            "group": kind,
            "color": _COLORS.get(kind, _DEFAULT_COLOR),
            "value": max(1, deg.get(nid, 1)),
            "level": level,
            "community": n.get("community_name") or "",
        })
    vedges = []
    for e in all_edges:
        s, t = e.get("source"), e.get("target")
        if s in kept and t in kept:
            vedges.append({
                "from": s, "to": t,
                "label": e.get("relation", ""),
                "arrows": "to",
                "confidence": e.get("confidence", ""),
                "dashes": e.get("confidence") == "INFERRED",
            })

    kinds_present = sorted({vn["group"] for vn in vnodes})
    legend = [{"kind": k, "color": _COLORS.get(k, _DEFAULT_COLOR)} for k in kinds_present]

    html = _TEMPLATE.replace("__NODES__", json.dumps(vnodes)) \
                    .replace("__EDGES__", json.dumps(vedges)) \
                    .replace("__LEGEND__", json.dumps(legend)) \
                    .replace("__STATS__", json.dumps({
                        "nodes_shown": len(vnodes),
                        "edges_shown": len(vedges),
                        "total_nodes": len(all_nodes),
                        "excluded_kinds": sorted(_EXCLUDE_KINDS),
                    }))
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html, encoding="utf-8")
    return {
        "html": str(out_html),
        "nodes_shown": len(vnodes),
        "edges_shown": len(vedges),
        "total_nodes": len(all_nodes),
        "kinds": kinds_present,
    }


_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Workday Build — Knowledge Graph</title>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
  html,body{margin:0;height:100%;font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#111;color:#eee}
  #top{padding:8px 12px;background:#1b1b1b;border-bottom:1px solid #333;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
  #top h1{font-size:15px;margin:0;font-weight:600}
  #search{padding:5px 8px;border-radius:5px;border:1px solid #444;background:#222;color:#eee;width:260px}
  #stats{font-size:12px;color:#999}
  button{background:#2a2a2a;color:#ddd;border:1px solid #444;border-radius:5px;padding:5px 9px;cursor:pointer}
  button:hover{background:#333}
  #wrap{display:flex;height:calc(100% - 46px)}
  #net{flex:1;height:100%}
  #legend{width:240px;overflow:auto;background:#161616;border-left:1px solid #333;padding:8px 10px;font-size:12px}
  .lg{display:flex;align-items:center;gap:6px;margin:2px 0;cursor:pointer}
  .sw{width:12px;height:12px;border-radius:3px;display:inline-block}
  #detail{margin-top:12px;padding-top:8px;border-top:1px solid #333;color:#bbb;white-space:pre-wrap;font-size:11px}
</style>
</head>
<body>
<div id="top">
  <h1>Workday Build — Knowledge Graph</h1>
  <input id="search" placeholder="Search nodes (label)…"/>
  <button id="fit">Fit</button>
  <button id="physics">Toggle physics</button>
  <button id="hideLeaves">Hide dangling refs</button>
  <span id="stats"></span>
</div>
<div id="wrap">
  <div id="net"></div>
  <div id="legend"><b>Node kinds</b><div id="legendItems"></div>
    <p style="color:#888;margin-top:10px">Click a legend row to isolate that kind (keeps neighbors). Dashed edges are inferred cross-refs. Hover or click a node for details.</p>
    <div id="detail"></div>
  </div>
</div>
<script>
const NODES=__NODES__, EDGES=__EDGES__, LEGEND=__LEGEND__, STATS=__STATS__;
document.getElementById('stats').textContent =
  `${STATS.nodes_shown} nodes / ${STATS.edges_shown} edges shown (of ${STATS.total_nodes} total; leaf kinds excluded)`;
const nodes=new vis.DataSet(NODES), edges=new vis.DataSet(EDGES);
const container=document.getElementById('net');
const data={nodes,edges};
let physicsOn=true;
const options={
  nodes:{shape:'dot',scaling:{min:8,max:42},font:{color:'#ddd',size:12},borderWidth:1,
         borderWidthSelected:2},
  edges:{color:{color:'#555',highlight:'#fff'},font:{color:'#888',size:9,strokeWidth:0},
         smooth:{type:'continuous'},arrows:{to:{scaleFactor:.4}}},
  physics:{
    stabilization:{iterations:220},
    barnesHut:{gravitationalConstant:-12000,springLength:140,springConstant:0.02,avoidOverlap:0.3}
  },
  interaction:{hover:true,tooltipDelay:120,navigationButtons:true,keyboard:true}
};
const network=new vis.Network(container,data,options);
document.getElementById('fit').onclick=()=>network.fit({animation:true});
document.getElementById('physics').onclick=()=>{physicsOn=!physicsOn;network.setOptions({physics:{enabled:physicsOn}});};

// Hide low-signal dangling ref nodes (deg 1 refs that only point at one thing).
const REF_KINDS=new Set(['task_ref','bo_ref','skill_ref','endpoint_invoke','subflow_ref']);
let leavesHidden=false;
document.getElementById('hideLeaves').onclick=()=>{
  leavesHidden=!leavesHidden;
  const deg={};
  EDGES.forEach(e=>{deg[e.from]=(deg[e.from]||0)+1;deg[e.to]=(deg[e.to]||0)+1;});
  nodes.update(NODES.map(n=>{
    const hide = leavesHidden && REF_KINDS.has(n.group) && (deg[n.id]||0)<=2;
    return {id:n.id, hidden:hide};
  }));
};

const search=document.getElementById('search');
search.oninput=()=>{
  const q=search.value.trim().toLowerCase();
  if(!q){nodes.update(NODES.map(n=>({id:n.id,hidden:false})));return;}
  const hitIds=new Set();
  NODES.forEach(n=>{ if(n.label.toLowerCase().includes(q) || (n.community||'').toLowerCase().includes(q)) hitIds.add(n.id); });
  // keep neighbors of hits so the match isn't an orphan island
  EDGES.forEach(e=>{ if(hitIds.has(e.from)) hitIds.add(e.to); if(hitIds.has(e.to)) hitIds.add(e.from); });
  nodes.update(NODES.map(n=>({id:n.id,hidden:!hitIds.has(n.id)})));
  const hit=NODES.find(n=>n.label.toLowerCase().includes(q));
  if(hit)network.focus(hit.id,{scale:1.1,animation:true});
};

const detail=document.getElementById('detail');
network.on('click', params=>{
  if(!params.nodes.length){detail.textContent='';return;}
  const n=NODES.find(x=>x.id===params.nodes[0]);
  if(n) detail.textContent=n.title || n.label;
});

const li=document.getElementById('legendItems');
let isolated=null;
LEGEND.forEach(l=>{
  const row=document.createElement('div');row.className='lg';
  row.innerHTML=`<span class="sw" style="background:${l.color}"></span>${l.kind}`;
  row.onclick=()=>{
    isolated = (isolated===l.kind)?null:l.kind;
    if(!isolated){ nodes.update(NODES.map(n=>({id:n.id,hidden:false}))); return; }
    // isolate kind BUT keep 1-hop neighbors so links stay visible
    const keep=new Set(NODES.filter(n=>n.group===isolated).map(n=>n.id));
    EDGES.forEach(e=>{ if(keep.has(e.from)) keep.add(e.to); if(keep.has(e.to)) keep.add(e.from); });
    nodes.update(NODES.map(n=>({id:n.id,hidden:!keep.has(n.id)})));
  };
  li.appendChild(row);
});
</script>
</body>
</html>
"""
