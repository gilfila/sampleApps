"""Deterministic extractors for Workday Extend artifacts.

These turn the reference sample apps into a knowledge graph of pages, widgets,
endpoints, business objects, orchestration steps, agents, and the relationships
between them — the "domain graph" that makes sample lookup smarter than grep.

Every file becomes a node; structural children (widgets, endpoints, fields,
steps, skills) become nodes linked back to their file, and cross-references
(task references, BO targets, skill tool usage) become edges.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .schema import Graph, CONF_EXTRACTED, CONF_INFERRED

# Workday Extend file extensions we understand.
WD_EXTENSIONS = {
    ".pmd", ".amd", ".smd", ".card", ".pod", ".script",
    ".businessobject", ".task", ".report", ".securitydomain",
    ".attachment", ".businessprocess", ".orchestration",
    ".suborchestration", ".agent", ".agentskill", ".wqlquery",
    ".carddefinition", ".json",
}

_EXT_KIND = {
    ".pmd": "pmd_page",
    ".amd": "app_metadata",
    ".smd": "site_metadata",
    ".card": "card",
    ".carddefinition": "card_definition",
    ".pod": "pod",
    ".script": "script",
    ".businessobject": "business_object",
    ".task": "task",
    ".report": "report",
    ".securitydomain": "security_domain",
    ".attachment": "attachment",
    ".businessprocess": "business_process",
    ".orchestration": "orchestration",
    ".suborchestration": "suborchestration",
    ".agent": "agent",
    ".agentskill": "agent_skill",
    ".wqlquery": "wql_query",
    ".json": "json_config",
}


def _load_json(path: Path):
    """Best-effort JSON load; Workday config files are JSON with <% %> strings."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _app_of(path: Path, root: Path) -> str:
    rel = _rel(path, root)
    return rel.split("/", 1)[0] if "/" in rel else rel


def _walk_widgets(node, out: list):
    """Recursively collect widget dicts that carry a 'type'."""
    if isinstance(node, dict):
        if "type" in node and isinstance(node["type"], str):
            out.append(node)
        for v in node.values():
            _walk_widgets(v, out)
    elif isinstance(node, list):
        for v in node:
            _walk_widgets(v, out)


def _find_task_refs(node, out: set):
    if isinstance(node, dict):
        tr = node.get("taskReference")
        if isinstance(tr, dict) and tr.get("taskId"):
            out.add(tr["taskId"])
        for v in node.values():
            _find_task_refs(v, out)
    elif isinstance(node, list):
        for v in node:
            _find_task_refs(v, out)


class WorkdayExtractor:
    def __init__(self, root: Path):
        self.root = root

    def extract(self, path: Path, g: Graph) -> None:
        ext = path.suffix.lower()
        kind = _EXT_KIND.get(ext, "file")
        rel = _rel(path, self.root)
        app = _app_of(path, self.root)
        file_id = f"file::{rel}"
        g.add_node(
            file_id,
            label=path.name,
            source_file=rel,
            source_location="L1",
            file_type=kind,
            kind=kind,
            community_name=app,
            text=f"{kind} in app {app}",
        )
        # App grouping node.
        app_id = f"app::{app}"
        g.add_node(app_id, label=app, source_file=app, file_type="app", kind="app", community_name=app)
        g.add_edge(app_id, file_id, "contains", CONF_EXTRACTED)

        handler = {
            ".pmd": self._pmd,
            ".amd": self._amd,
            ".script": self._script,
            ".businessobject": self._businessobject,
            ".orchestration": self._orchestration,
            ".suborchestration": self._orchestration,
            ".agent": self._agent,
            ".agentskill": self._agentskill,
            ".card": self._generic_json,
            ".pod": self._generic_json,
            ".report": self._generic_json,
            ".task": self._task,
            ".businessprocess": self._generic_json,
        }.get(ext)
        if handler:
            try:
                handler(path, g, file_id, rel, app)
            except Exception:
                pass

    # ---- per-type ----------------------------------------------------------
    def _pmd(self, path, g, file_id, rel, app):
        data = _load_json(path)
        if not isinstance(data, dict):
            return
        # endpoints
        for ep in (data.get("endPoints") or []):
            if not isinstance(ep, dict):
                continue
            name = ep.get("name", "endpoint")
            eid = f"endpoint::{rel}::{name}"
            g.add_node(eid, label=f"{name} ({ep.get('baseUrlType','')})", source_file=rel,
                       file_type="endpoint", kind="endpoint",
                       community_name=app, text=json.dumps(ep)[:500])
            g.add_edge(file_id, eid, "declares_endpoint", CONF_EXTRACTED)
            bu = ep.get("baseUrlType")
            if bu:
                bid = f"baseurl::{bu}"
                g.add_node(bid, label=bu, file_type="base_url", kind="base_url", community_name="api")
                g.add_edge(eid, bid, "uses_base_url", CONF_EXTRACTED)
        # outbound endpoints
        for ep in ((data.get("outboundData") or {}).get("outboundEndPoints") or []):
            if not isinstance(ep, dict):
                continue
            name = ep.get("name", "outbound")
            eid = f"outbound::{rel}::{name}"
            g.add_node(eid, label=f"{name} ({ep.get('httpMethod','')})", source_file=rel,
                       file_type="outbound_endpoint", kind="outbound_endpoint",
                       community_name=app, text=json.dumps(ep)[:500])
            g.add_edge(file_id, eid, "declares_outbound", CONF_EXTRACTED)
        # widgets
        widgets: list = []
        _walk_widgets(data.get("presentation", data), widgets)
        seen_types: set = set()
        for w in widgets:
            wtype = w.get("type")
            if not wtype or wtype in seen_types:
                continue
            seen_types.add(wtype)
            wid = f"widget::{wtype}"
            g.add_node(wid, label=wtype, file_type="widget_type", kind="widget_type",
                       community_name="widgets", text=f"PMD widget type {wtype}")
            g.add_edge(file_id, wid, "uses_widget", CONF_EXTRACTED)
        # task references
        refs: set = set()
        _find_task_refs(data, refs)
        for t in refs:
            tid = f"taskref::{t}"
            g.add_node(tid, label=t, file_type="task_ref", kind="task_ref", community_name=app)
            g.add_edge(file_id, tid, "navigates_to", CONF_INFERRED)

    def _amd(self, path, g, file_id, rel, app):
        data = _load_json(path)
        if not isinstance(data, dict):
            return
        for t in (data.get("tasks") or []):
            if isinstance(t, dict) and t.get("id"):
                tid = f"task::{app}::{t['id']}"
                page = t.get("page") if isinstance(t.get("page"), dict) else {}
                page_id = page.get("id") or t.get("id")
                g.add_node(tid, label=t["id"], source_file=rel, file_type="task", kind="task",
                           community_name=app, text=json.dumps(t)[:300])
                # Stash page id for the cross-ref resolver.
                g.nodes[tid]["page_id"] = page_id
                g.add_edge(file_id, tid, "defines_task", CONF_EXTRACTED)
        for f in (data.get("flows") or data.get("flowDefinitions") or []):
            if isinstance(f, dict) and f.get("id"):
                fid = f"flow::{app}::{f['id']}"
                g.add_node(fid, label=f["id"], source_file=rel, file_type="flow", kind="flow",
                           community_name=app, text=json.dumps(f)[:400])
                g.add_edge(file_id, fid, "defines_flow", CONF_EXTRACTED)
        for dp in (data.get("dataProviders") or []):
            if isinstance(dp, dict) and dp.get("key"):
                did = f"dataprovider::{dp['key']}"
                g.add_node(did, label=dp["key"], file_type="data_provider", kind="data_provider",
                           community_name="api", text=str(dp.get("value", ""))[:300])
                g.add_edge(file_id, did, "wires_provider", CONF_EXTRACTED)

    def _task(self, path, g, file_id, rel, app):
        data = _load_json(path)
        if isinstance(data, dict) and data.get("businessObject"):
            g.add_edge(file_id, f"boref::{data['businessObject']}", "targets_bo", CONF_EXTRACTED)
            g.add_node(f"boref::{data['businessObject']}", label=data["businessObject"],
                       file_type="bo_ref", kind="bo_ref", community_name=app)

    def _businessobject(self, path, g, file_id, rel, app):
        data = _load_json(path)
        if not isinstance(data, dict):
            return
        boname = data.get("name", path.stem)
        bo_id = f"bo::{boname}"
        g.add_node(bo_id, label=boname, source_file=rel, file_type="business_object",
                   kind="business_object", community_name=app, text=json.dumps(data)[:500])
        g.add_edge(file_id, bo_id, "defines_bo", CONF_EXTRACTED)
        for fld in (data.get("fields") or []):
            if isinstance(fld, dict) and fld.get("name"):
                fid = f"field::{boname}::{fld['name']}"
                g.add_node(fid, label=f"{fld['name']}:{fld.get('type','')}", source_file=rel,
                           file_type="bo_field", kind="bo_field", community_name=app,
                           text=json.dumps(fld)[:200])
                g.add_edge(bo_id, fid, "has_field", CONF_EXTRACTED)
                if fld.get("target"):
                    g.add_edge(fid, f"boref::{fld['target']}", "references", CONF_EXTRACTED)

    def _orchestration(self, path, g, file_id, rel, app):
        data = _load_json(path)
        if not isinstance(data, dict):
            data = {}
        raw = json.dumps(data)

        # Maya Flow format: {_type:"Flow", _value:{id, name, nodes...}}
        flow = data.get("_value") if data.get("_type") == "Flow" else data
        if not isinstance(flow, dict):
            flow = {}

        def _maya_str(node):
            if isinstance(node, dict) and "_value" in node:
                v = node["_value"]
                return v if isinstance(v, str) else None
            return node if isinstance(node, str) else None

        flow_id = _maya_str(flow.get("id")) or data.get("id")
        flow_name = _maya_str(flow.get("name")) or data.get("name") or path.stem
        if flow_id:
            g.nodes[file_id]["flow_id"] = flow_id
            g.nodes[file_id]["label"] = flow_name
        g.nodes[file_id]["text"] = f"{path.suffix[1:]} {flow_name} id={flow_id or ''}"

        # Simple list-of-steps shape (non-Maya)
        steps = data.get("steps")
        if isinstance(steps, list):
            for s in steps[:60]:
                if isinstance(s, dict):
                    sid = s.get("id") or s.get("name")
                    if sid:
                        nid = f"orchstep::{rel}::{sid}"
                        g.add_node(nid, label=str(sid), source_file=rel, file_type="orch_step",
                                   kind="orch_step", community_name=app)
                        g.add_edge(file_id, nid, "has_step", CONF_EXTRACTED)

        # Maya CallSubflow nodes — name + UUID
        # Pattern A: "subflowId":{"_type":"String","_value":"<uuid>"}
        # Pattern B: flat "subflowId":"<uuid>"
        uuid_hits = set(re.findall(
            r'"subflowId"\s*:\s*(?:\{\s*"_type"\s*:\s*"String"\s*,\s*"_value"\s*:\s*"([^"]+)"|"([^"]+)")',
            raw,
        ))
        sub_ids = {a or b for a, b in uuid_hits if (a or b)}
        # Also capture CallSubflow display names for readability
        call_names = re.findall(
            r'"_type"\s*:\s*"CallSubflow".*?"name"\s*:\s*\{\s*"_type"\s*:\s*"Identifier"\s*,\s*"_value"\s*:\s*"([^"]+)"',
            raw,
        )
        for i, sub in enumerate(sorted(sub_ids)):
            ref_id = f"subflow::{app}::{sub}"
            label = call_names[i] if i < len(call_names) else sub
            g.add_node(ref_id, label=sub, source_file=rel, file_type="subflow_ref",
                       kind="subflow_ref", community_name=app,
                       text=f"CallSubflow {label}")
            # Keep UUID as label for resolver; stash human name in text.
            g.add_edge(file_id, ref_id, "calls_subflow", CONF_EXTRACTED)

    def _script(self, path, g, file_id, rel, app):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'var\s+([A-Za-z_$][\w$]*)\s*=\s*function', text):
            fn = m.group(1)
            line = text[: m.start()].count("\n") + 1
            fid = f"scriptfn::{rel}::{fn}"
            g.add_node(fid, label=fn, source_file=rel, source_location=f"L{line}",
                       file_type="script_function", kind="script_function", community_name=app)
            g.add_edge(file_id, fid, "defines_function", CONF_EXTRACTED)
        for ep in set(re.findall(r'([A-Za-z_$][\w$]*)\.invoke\s*\(', text)):
            g.add_edge(file_id, f"endpoint_invoke::{ep}", "invokes_endpoint", CONF_INFERRED)
            g.add_node(f"endpoint_invoke::{ep}", label=ep, file_type="endpoint_invoke",
                       kind="endpoint_invoke", community_name=app)

    def _agent(self, path, g, file_id, rel, app):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for skill in re.findall(r'^\s*-\s+([a-z0-9][a-z0-9\-]+)\s*$', text, re.MULTILINE):
            g.add_edge(file_id, f"skillref::{skill}", "uses_skill", CONF_EXTRACTED)
            g.add_node(f"skillref::{skill}", label=skill, file_type="skill_ref", kind="skill_ref",
                       community_name=app)

    def _agentskill(self, path, g, file_id, rel, app):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for tool in re.findall(r'^\s*-\s+([a-z][a-zA-Z0-9_]+)\s*$', text):
            if tool in ("name", "wid"):
                continue
            g.add_edge(file_id, f"tool::{tool}", "allowed_tool", CONF_EXTRACTED)
            g.add_node(f"tool::{tool}", label=tool, file_type="agent_tool", kind="agent_tool",
                       community_name="agent_tools")

    def _generic_json(self, path, g, file_id, rel, app):
        # Index a short text blob for search; no extra structure.
        data = _load_json(path)
        if isinstance(data, dict):
            g.nodes[file_id]["text"] = json.dumps(data)[:1200]


def build_reference_graph(reference_dir: Path) -> Graph:
    g = Graph()
    if not reference_dir.exists():
        return g
    ex = WorkdayExtractor(reference_dir)
    for path in sorted(reference_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in WD_EXTENSIONS:
            if "/.git/" in str(path):
                continue
            ex.extract(path, g)
    return g
