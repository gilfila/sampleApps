"""Graph-backed query engine.

Loads the Graphify-compatible `graph.json` and answers questions by:
  1. scoring nodes against query terms (exact/prefix/substring + text match),
  2. seeding a bounded BFS from the top matches,
  3. returning ranked results with source file, location, and excerpt.

This is the "graph-backed, not naive grep" layer: results are ranked by graph
relevance and enriched with neighboring context (endpoints a page uses, fields
a BO has, sections a topic contains).
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from .. import config

_WORD = re.compile(r"\w+")
_STOP = {
    "the", "a", "an", "how", "do", "i", "to", "in", "of", "for", "and", "or",
    "is", "are", "with", "on", "use", "using", "create", "make", "build",
    "workday", "extend", "example", "examples", "show", "me", "can",
}


def _terms(q: str) -> list[str]:
    toks = [t.lower() for t in _WORD.findall(q)]
    content = [t for t in toks if len(t) > 2 and t not in _STOP]
    return content or [t for t in toks if len(t) > 1] or toks


class GraphIndex:
    def __init__(self, data: dict):
        self.nodes: dict[str, dict] = {n["id"]: n for n in data.get("nodes", [])}
        self.adj: dict[str, list[tuple[str, str]]] = defaultdict(list)
        self.radj: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for e in (data.get("links") or data.get("edges") or []):
            s, t, r = e.get("source"), e.get("target"), e.get("relation", "")
            if s in self.nodes and t in self.nodes:
                self.adj[s].append((t, r))
                self.radj[t].append((s, r))
        # precompute searchable text
        self._search: dict[str, str] = {}
        for nid, n in self.nodes.items():
            self._search[nid] = " ".join([
                n.get("label", ""), n.get("source_file", ""),
                n.get("kind", ""), n.get("text", ""),
            ]).lower()

    def degree(self, nid: str) -> int:
        return len(self.adj.get(nid, ())) + len(self.radj.get(nid, ()))

    def score(self, terms: list[str], kinds: set[str] | None = None) -> list[tuple[float, str]]:
        scored: list[tuple[float, str]] = []
        for nid, n in self.nodes.items():
            if kinds and n.get("kind") not in kinds:
                continue
            label = n.get("label", "").lower()
            text = self._search[nid]
            s = 0.0
            matched = 0
            for t in terms:
                if t == label:
                    s += 100; matched += 1
                elif label.startswith(t):
                    s += 40; matched += 1
                elif t in label:
                    s += 15; matched += 1
                elif t in text:
                    s += 4; matched += 1
            if matched:
                s *= (matched / len(terms)) ** 2 if len(terms) else 1
                s += min(self.degree(nid), 20) * 0.1
                scored.append((s, nid))
        scored.sort(key=lambda x: (-x[0], len(self.nodes[x[1]].get("label", ""))))
        return scored

    def neighbors(self, nid: str) -> list[tuple[str, str, str]]:
        out = []
        for t, r in self.adj.get(nid, []):
            out.append((r, "->", t))
        for s, r in self.radj.get(nid, []):
            out.append((r, "<-", s))
        return out

    def bfs(self, seeds: list[str], depth: int = 1, limit: int = 40) -> list[str]:
        seen = list(seeds)
        seen_set = set(seeds)
        frontier = list(seeds)
        for _ in range(depth):
            nxt = []
            for n in frontier:
                for t, _r in self.adj.get(n, []):
                    if t not in seen_set:
                        seen_set.add(t); nxt.append(t); seen.append(t)
                for s, _r in self.radj.get(n, []):
                    if s not in seen_set:
                        seen_set.add(s); nxt.append(s); seen.append(s)
                if len(seen) >= limit:
                    return seen[:limit]
            frontier = nxt
        return seen[:limit]


@lru_cache(maxsize=1)
def _load(mtime_key: float) -> GraphIndex:
    data = json.loads(config.GRAPH_JSON.read_text(encoding="utf-8"))
    return GraphIndex(data)


def load_index() -> GraphIndex | None:
    if not config.GRAPH_JSON.exists():
        return None
    return _load(config.GRAPH_JSON.stat().st_mtime)


def _fmt_node(idx: GraphIndex, nid: str, with_neighbors: bool = False) -> str:
    n = idx.nodes[nid]
    head = f"[{n.get('kind','')}] {n.get('label','')}"
    src = n.get("source_file", "")
    loc = n.get("source_location", "")
    if src:
        head += f"  ({src}{':' + loc if loc else ''})"
    lines = [head]
    txt = (n.get("text") or "").strip()
    if txt and txt != n.get("label", ""):
        snippet = txt.replace("\n", " ")[:280]
        lines.append(f"    {snippet}")
    if with_neighbors:
        nbrs = idx.neighbors(nid)[:8]
        for rel, arrow, other in nbrs:
            lines.append(f"    {arrow} {rel}: {idx.nodes[other].get('label', other)}")
    return "\n".join(lines)


def query(question: str, kinds: set[str] | None = None, top_k: int = 8,
          with_neighbors: bool = True) -> str:
    idx = load_index()
    if idx is None:
        return ("No knowledge graph found. Run the `rebuild_graph` tool "
                "(or `python -m workday_build_mcp.graph` build) first.")
    terms = _terms(question)
    scored = idx.score(terms, kinds=kinds)
    if not scored:
        return f"No matches for: {question!r} (terms: {terms})."
    results = [nid for _s, nid in scored[:top_k]]
    header = f"Top {len(results)} matches for {question!r} (graph-ranked):\n"
    body = "\n\n".join(_fmt_node(idx, nid, with_neighbors) for nid in results)
    return header + "\n" + body
