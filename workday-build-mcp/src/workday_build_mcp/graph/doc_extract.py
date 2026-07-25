"""Documentation graph extractor.

Parses the local Workday Extend documentation / forum markdown corpus into a
graph of topic -> section nodes. Section nodes carry an excerpt so the query
engine can return real doc content, not just filenames.

Optional Graphify enrichment: if the `graphify` CLI is installed, we also run
it over the docs directory and merge its markdown link/heading graph, giving
higher-fidelity cross-references. This is best-effort and never required.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .schema import Graph, CONF_EXTRACTED, CONF_INFERRED, iter_edges

_HEADING = re.compile(r"^(#{1,4})\s+(.*)$")


def _topic_of(name: str) -> str:
    # e.g. "orchestrations_forum_posts-part-03.md" -> "orchestrations"
    stem = name.rsplit(".", 1)[0]
    return re.split(r"[_-]", stem)[0]


def build_docs_graph(docs_dir: Path, max_section_chars: int = 1200) -> Graph:
    g = Graph()
    if not docs_dir.exists():
        return g
    for path in sorted(docs_dir.glob("*.md")):
        rel = path.name
        topic = _topic_of(path.name)
        topic_id = f"doctopic::{topic}"
        g.add_node(topic_id, label=topic, file_type="doc_topic", kind="doc_topic",
                   community_name="docs", text=f"Documentation topic: {topic}")
        doc_id = f"doc::{rel}"
        g.add_node(doc_id, label=rel, source_file=rel, source_location="L1",
                   file_type="doc_file", kind="doc_file", community_name="docs",
                   text=f"Documentation file {rel}")
        g.add_edge(topic_id, doc_id, "contains", CONF_EXTRACTED)

        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        cur_id = None
        cur_heading = ""
        cur_line = 1
        buf: list[str] = []

        def flush(section_id, start_line, heading, body):
            if not section_id:
                return
            excerpt = "\n".join(body).strip()[:max_section_chars]
            g.add_node(section_id, label=heading[:120], source_file=rel,
                       source_location=f"L{start_line}", file_type="doc_section",
                       kind="doc_section", community_name="docs",
                       text=(heading + "\n" + excerpt)[:max_section_chars])
            g.add_edge(doc_id, section_id, "has_section", CONF_EXTRACTED)

        sec_count = 0
        for i, line in enumerate(lines, 1):
            m = _HEADING.match(line)
            if m:
                flush(cur_id, cur_line, cur_heading, buf)
                heading = m.group(2).strip()
                sec_count += 1
                cur_id = f"docsec::{rel}::{sec_count}"
                cur_heading = heading
                cur_line = i
                buf = []
            else:
                if len(buf) < 60:
                    buf.append(line)
        flush(cur_id, cur_line, cur_heading, buf)
    return g


def graphify_enrich(docs_dir: Path) -> Graph | None:
    """Best-effort: run the `graphify` CLI over docs and merge its graph.

    Returns None when graphify is unavailable or fails — callers fall back to
    the deterministic docs graph.
    """
    exe = shutil.which("graphify")
    if not exe:
        return None
    try:
        out_dir = Path(tempfile.mkdtemp(prefix="graphify_docs_"))
        subprocess.run(
            [exe, "extract", str(docs_dir), "--out", str(out_dir)],
            check=True, capture_output=True, timeout=900,
        )
        graph_json = out_dir / "graph.json"
        if not graph_json.exists():
            # graphify default output dir
            cand = list(out_dir.rglob("graph.json"))
            if not cand:
                return None
            graph_json = cand[0]
        data = json.loads(graph_json.read_text(encoding="utf-8"))
        g = Graph()
        for n in data.get("nodes", []):
            nid = f"gfy::{n.get('id')}"
            g.add_node(nid, label=n.get("label", ""), source_file=n.get("source_file", ""),
                       source_location=n.get("source_location", ""),
                       file_type=n.get("file_type", ""), kind="graphify_" + str(n.get("file_type", "node")),
                       community_name="docs", text=n.get("label", ""))
        for e in iter_edges(data):
            g.add_edge(f"gfy::{e.get('source')}", f"gfy::{e.get('target')}",
                       e.get("relation", "related"), CONF_INFERRED)
        return g
    except Exception:
        return None
