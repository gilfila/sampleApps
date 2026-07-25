"""Graphify-compatible node-link graph structures.

We emit the exact same JSON shape that Graphify's `graph.json` uses
(NetworkX node-link with `directed: true`), so the resulting graph can be
served by `graphify-mcp` as well as by this package's own query engine.

Node schema:
    {"id", "label", "source_file", "source_location", "file_type",
     "kind", "community", "community_name", "text"}
Edge schema (under "links"):
    {"source", "target", "relation", "confidence"}
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


CONF_EXTRACTED = "EXTRACTED"
CONF_INFERRED = "INFERRED"
CONF_AMBIGUOUS = "AMBIGUOUS"


@dataclass
class Graph:
    nodes: dict[str, dict] = field(default_factory=dict)
    edges: list[dict] = field(default_factory=list)
    _edge_keys: set = field(default_factory=set)

    def add_node(
        self,
        node_id: str,
        label: str,
        *,
        source_file: str = "",
        source_location: str = "",
        file_type: str = "",
        kind: str = "",
        community: int | None = None,
        community_name: str = "",
        text: str = "",
    ) -> str:
        if node_id not in self.nodes:
            self.nodes[node_id] = {
                "id": node_id,
                "label": label[:256],
                "source_file": source_file,
                "source_location": source_location,
                "file_type": file_type,
                "kind": kind,
                "text": text[:2000],
            }
            if community is not None:
                self.nodes[node_id]["community"] = community
            if community_name:
                self.nodes[node_id]["community_name"] = community_name
        return node_id

    def add_edge(
        self,
        source: str,
        target: str,
        relation: str,
        confidence: str = CONF_EXTRACTED,
    ) -> None:
        if source == target:
            return
        key = (source, target, relation)
        if key in self._edge_keys:
            return
        self._edge_keys.add(key)
        self.edges.append(
            {
                "source": source,
                "target": target,
                "relation": relation,
                "confidence": confidence,
            }
        )

    def merge(self, other: "Graph") -> None:
        for nid, data in other.nodes.items():
            if nid not in self.nodes:
                self.nodes[nid] = data
        for e in other.edges:
            self.add_edge(e["source"], e["target"], e["relation"], e.get("confidence", CONF_EXTRACTED))

    def to_node_link(self) -> dict:
        return {
            "directed": True,
            "multigraph": False,
            "graph": {},
            "nodes": list(self.nodes.values()),
            "links": self.edges,
        }

    def stats(self) -> dict:
        kinds: dict[str, int] = {}
        for n in self.nodes.values():
            kinds[n.get("kind", "")] = kinds.get(n.get("kind", ""), 0) + 1
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "kinds": dict(sorted(kinds.items(), key=lambda kv: -kv[1])),
        }


def iter_edges(data: dict) -> Iterable[dict]:
    return data.get("links") or data.get("edges") or []
