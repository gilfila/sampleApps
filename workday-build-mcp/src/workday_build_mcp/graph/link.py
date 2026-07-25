"""Resolve cross-references so the knowledge graph is navigable, not a star forest.

The raw extractors emit containment edges (app→file→child) plus *dangling* ref
nodes (task_ref, bo_ref, skill_ref, endpoint_invoke, subflow UUID). This pass:

1. Resolves refs onto their real targets (same-app preferred).
2. Links AMD tasks to their PMD pages.
3. Bridges documentation topics to related sample apps.
4. Adds a single platform hub so docs + samples share one connected component
   for visualization (without inventing fake domain relationships).
"""
from __future__ import annotations

import re
from collections import defaultdict

from .schema import Graph, CONF_INFERRED, CONF_EXTRACTED

# Topic keyword → sample signals (app name substrings / file kinds / labels).
_DOC_TOPIC_SIGNALS: dict[str, tuple[str, ...]] = {
    "orchestrat": ("orchestrat", "suborchestration", "orchestration"),
    "pmd": ("pmd", "widget", "presentation", "scripting"),
    "widget": ("widget", "pmd"),
    "script": ("script", "pmdScripting"),
    "agent": ("agent", "a2ui"),
    "business": ("businessobject", "business_object", "bo"),
    "security": ("security",),
    "card": ("card",),
    "pod": ("pod",),
    "extend": ("pmd", "extend", "app"),
    "integrat": ("orchestrat", "integrat"),
    "forum": (),  # generic; bridged via platform hub only
}


def resolve_cross_references(g: Graph) -> dict:
    """Mutate *g* in place. Returns counts of links created."""
    counts: dict[str, int] = defaultdict(int)

    by_kind: dict[str, list[str]] = defaultdict(list)
    by_label: dict[str, list[str]] = defaultdict(list)
    for nid, n in g.nodes.items():
        by_kind[n.get("kind", "")].append(nid)
        label = (n.get("label") or "").strip()
        if label:
            by_label[label.lower()].append(nid)

    def _same_app(a: str, b: str) -> bool:
        return (g.nodes[a].get("community_name") or "") == (g.nodes[b].get("community_name") or "")

    def _pick(candidates: list[str], from_id: str) -> str | None:
        if not candidates:
            return None
        same = [c for c in candidates if _same_app(from_id, c)]
        pool = same or candidates
        return pool[0]

    # ---- task_ref → task ---------------------------------------------------
    tasks_by_label: dict[str, list[str]] = defaultdict(list)
    for tid in by_kind.get("task", []):
        tasks_by_label[g.nodes[tid]["label"].lower()].append(tid)
    for rid in by_kind.get("task_ref", []):
        label = g.nodes[rid]["label"].lower()
        target = _pick(tasks_by_label.get(label, []), rid)
        if target:
            g.add_edge(rid, target, "resolves_to", CONF_INFERRED)
            counts["task_ref→task"] += 1

    # ---- bo_ref → business_object ------------------------------------------
    bos_by_label: dict[str, list[str]] = defaultdict(list)
    for bid in by_kind.get("business_object", []):
        bos_by_label[g.nodes[bid]["label"].lower()].append(bid)
    for rid in by_kind.get("bo_ref", []):
        label = g.nodes[rid]["label"].lower()
        target = _pick(bos_by_label.get(label, []), rid)
        if target:
            g.add_edge(rid, target, "resolves_to", CONF_INFERRED)
            counts["bo_ref→bo"] += 1

    # ---- skill_ref → agent_skill file --------------------------------------
    skills_by_label: dict[str, list[str]] = defaultdict(list)
    for sid in by_kind.get("agent_skill", []):
        skills_by_label[g.nodes[sid]["label"].lower().removesuffix(".agentskill")].append(sid)
        skills_by_label[g.nodes[sid]["label"].lower()].append(sid)
    for rid in by_kind.get("skill_ref", []):
        label = g.nodes[rid]["label"].lower()
        target = _pick(skills_by_label.get(label, []), rid)
        if target:
            g.add_edge(rid, target, "resolves_to", CONF_INFERRED)
            counts["skill_ref→skill"] += 1

    # ---- endpoint_invoke → endpoint ----------------------------------------
    eps_by_label: dict[str, list[str]] = defaultdict(list)
    for eid in by_kind.get("endpoint", []) + by_kind.get("outbound_endpoint", []):
        # labels look like "getWorkers (RELATIVE)" — match on the name prefix
        raw = g.nodes[eid]["label"]
        name = raw.split(" (", 1)[0].strip().lower()
        eps_by_label[name].append(eid)
        # also index the id segment after last ::
        eps_by_label[eid.rsplit("::", 1)[-1].lower()].append(eid)
    for rid in by_kind.get("endpoint_invoke", []):
        label = g.nodes[rid]["label"].lower()
        target = _pick(eps_by_label.get(label, []), rid)
        if target:
            g.add_edge(rid, target, "resolves_to", CONF_INFERRED)
            counts["invoke→endpoint"] += 1

    # ---- subflow UUID → suborchestration file ------------------------------
    orch_by_flow_id: dict[str, str] = {}
    for nid, n in g.nodes.items():
        fid = n.get("flow_id")
        if fid:
            orch_by_flow_id[fid] = nid
    for rid in by_kind.get("subflow_ref", []):
        # label is the UUID (or name)
        key = g.nodes[rid]["label"]
        target = orch_by_flow_id.get(key)
        if not target:
            # try match by flow name
            target = _pick(by_label.get(key.lower(), []), rid)
            if target and g.nodes[target].get("kind") not in (
                "suborchestration", "orchestration", "orch_step"
            ):
                target = None
        if target:
            g.add_edge(rid, target, "resolves_to", CONF_INFERRED)
            counts["subflow→orch"] += 1

    # ---- task → pmd_page (via page id / stem) ------------------------------
    pages_by_stem: dict[str, list[str]] = defaultdict(list)
    for pid in by_kind.get("pmd_page", []):
        stem = g.nodes[pid]["label"].removesuffix(".pmd").lower()
        pages_by_stem[stem].append(pid)
        # also index source_file basename
        sf = (g.nodes[pid].get("source_file") or "").rsplit("/", 1)[-1]
        pages_by_stem[sf.removesuffix(".pmd").lower()].append(pid)
    for tid in by_kind.get("task", []):
        n = g.nodes[tid]
        page_id = (n.get("page_id") or n.get("label") or "").lower()
        target = _pick(pages_by_stem.get(page_id, []), tid)
        if target:
            g.add_edge(tid, target, "opens_page", CONF_INFERRED)
            counts["task→page"] += 1

    # ---- docs ↔ samples (topic signals) ------------------------------------
    apps = by_kind.get("app", [])
    for topic_id in by_kind.get("doc_topic", []):
        topic = g.nodes[topic_id]["label"].lower()
        signals: list[str] = []
        for key, vals in _DOC_TOPIC_SIGNALS.items():
            if key in topic:
                signals.extend(vals)
        if not signals:
            # use the topic token itself
            signals = [topic]
        linked_apps = set()
        for app_id in apps:
            app_label = g.nodes[app_id]["label"].lower()
            # also look at kinds present under this app community
            if any(sig and sig in app_label for sig in signals):
                g.add_edge(topic_id, app_id, "documents", CONF_INFERRED)
                linked_apps.add(app_id)
                counts["doc→app"] += 1
        # If nothing matched by app name, link topic to apps that contain
        # matching artifact kinds (e.g. orchestrations topic → orch apps).
        if not linked_apps:
            kind_hits = set()
            for sig in signals:
                for kind, nids in by_kind.items():
                    if sig in kind:
                        for nid in nids:
                            community = g.nodes[nid].get("community_name")
                            if community:
                                kind_hits.add(community)
            for app_id in apps:
                if g.nodes[app_id]["label"] in kind_hits or g.nodes[app_id].get("community_name") in kind_hits:
                    g.add_edge(topic_id, app_id, "documents", CONF_INFERRED)
                    counts["doc→app"] += 1

    # ---- platform hub (one connected component for viz) --------------------
    hub = "platform::workday_build"
    g.add_node(
        hub,
        label="Workday Build",
        file_type="platform",
        kind="platform",
        community_name="platform",
        text="Root hub linking sample apps and documentation topics",
    )
    for app_id in apps:
        g.add_edge(hub, app_id, "includes_app", CONF_EXTRACTED)
        counts["hub→app"] += 1
    for topic_id in by_kind.get("doc_topic", []):
        g.add_edge(hub, topic_id, "includes_docs", CONF_EXTRACTED)
        counts["hub→docs"] += 1

    return dict(counts)
