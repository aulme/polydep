# ruff: noqa: E501
import json
import tempfile
import webbrowser
from pathlib import Path

from polydep.models import BrickType, DependencyGraph
from polydep.parse_mermaid import parse_mermaid_with_subgraphs

PALETTE = [
    {"bg": "#7c2d12", "border": "#f97316"},  # orange
    {"bg": "#1e3a5f", "border": "#60a5fa"},  # blue
    {"bg": "#14532d", "border": "#4ade80"},  # green
    {"bg": "#4c1d95", "border": "#c084fc"},  # purple
    {"bg": "#831843", "border": "#f472b6"},  # pink
    {"bg": "#713f12", "border": "#fbbf24"},  # yellow
]
UNASSIGNED = {"bg": "#1f2937", "border": "#6b7280"}


def _find_cycles(edges: list[tuple[str, str]]) -> list[list[str]]:
    """Port of findSimpleCycles from fishtail/src/generate-html.ts."""
    adj: dict[str, list[str]] = {}
    all_nodes: set[str] = set()
    for source, target in edges:
        all_nodes.add(source)
        all_nodes.add(target)
        adj.setdefault(source, []).append(target)

    # Tarjan's SCC
    index: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    scc_nodes: dict[int, list[str]] = {}
    counter = [0]
    scc_count = [0]

    def strongconnect(v: str) -> None:
        index[v] = counter[0]
        lowlink[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        for w in adj.get(v, []):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], index[w])
        if lowlink[v] == index[v]:
            scc = scc_count[0]
            scc_count[0] += 1
            members: list[str] = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                members.append(w)
                if w == v:
                    break
            scc_nodes[scc] = members

    for node in all_nodes:
        if node not in index:
            strongconnect(node)

    seen: set[str] = set()
    cycles: list[list[str]] = []

    # Self-loops
    for source, target in edges:
        if source == target:
            key = json.dumps([source])
            if key not in seen:
                seen.add(key)
                cycles.append([source])

    # DFS helper — defined once here (not inside any loop) to satisfy B023.
    # `seen` and `cycles` are captured from the enclosing scope; all
    # loop-dependent state is passed explicitly as parameters.
    def dfs(
        current: str,
        start: str,
        path: list[str],
        visited: set[str],
        scc_adj: dict[str, list[str]],
    ) -> None:
        for neighbor in scc_adj.get(current, []):
            if neighbor == start and len(path) > 1:
                min_idx = min(range(len(path)), key=lambda i: path[i])
                canonical = path[min_idx:] + path[:min_idx]
                canon_key = json.dumps(canonical)
                if canon_key not in seen:
                    seen.add(canon_key)
                    cycles.append(canonical[:])
            elif neighbor not in visited:
                visited.add(neighbor)
                path.append(neighbor)
                dfs(neighbor, start, path, visited, scc_adj)
                path.pop()
                visited.discard(neighbor)

    # Multi-node cycles via DFS within each SCC
    for members in scc_nodes.values():
        if len(members) <= 1:
            continue
        scc_set = set(members)
        scc_adj: dict[str, list[str]] = {
            node: [n for n in adj.get(node, []) if n in scc_set] for node in members
        }
        for start in members:
            dfs(start, start, [start], {start}, scc_adj)

    cycles.sort(key=lambda c: (len(c), ",".join(c)))
    return cycles


def _find_groups(edges: list[tuple[str, str]], node_ids: list[str]) -> list[list[str]]:
    """Port of findGroups from fishtail/src/generate-html.ts (Union-Find)."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for node_id in node_ids:
        find(node_id)
    for source, target in edges:
        union(source, target)

    groups: dict[str, list[str]] = {}
    for node_id in node_ids:
        root = find(node_id)
        groups.setdefault(root, []).append(node_id)

    return sorted([sorted(g) for g in groups.values()], key=lambda g: -len(g))


def _build_view_data(
    node_subgraph: dict[str, str],
    edges: list[tuple[str, str]],
) -> dict:
    """Build the __FISHTAIL_DATA__ dict from node/subgraph/edge inputs."""
    # Collect all node IDs (from subgraph membership and from edges)
    all_node_ids: list[str] = sorted({*node_subgraph.keys(), *(n for e in edges for n in e)})

    # Assign palette colors per subgraph (in insertion order of first seen subgraph)
    subgraph_order: list[str] = []
    for node_id in all_node_ids:
        sg = node_subgraph.get(node_id)
        if sg is not None and sg not in subgraph_order:
            subgraph_order.append(sg)

    subgraph_colors: dict[str, dict[str, str]] = {
        sg: PALETTE[i % len(PALETTE)] for i, sg in enumerate(subgraph_order)
    }

    nodes = []
    for node_id in all_node_ids:
        sg = node_subgraph.get(node_id)
        colors = subgraph_colors.get(sg, UNASSIGNED) if sg else UNASSIGNED
        nodes.append(
            {
                "data": {
                    "id": node_id,
                    "label": node_id,
                    "subgraph": sg,
                    "bgColor": colors["bg"],
                    "borderColor": colors["border"],
                    "dotColor": colors["border"],
                }
            }
        )

    edge_list = [{"data": {"id": f"{s}__{t}", "source": s, "target": t}} for s, t in edges]

    legend = [{"name": sg, "color": subgraph_colors[sg]["border"]} for sg in subgraph_order]

    cycles = _find_cycles(edges)
    groups = _find_groups(edges, all_node_ids)

    return {
        "nodes": nodes,
        "edges": edge_list,
        "legend": legend,
        "cycles": cycles,
        "groups": groups,
    }


def _generate_html(data: dict, title: str) -> str:
    """Generate self-contained HTML with inlined viewer bundle."""
    data_json = json.dumps(data)
    bundle_path = Path(__file__).parent / "static" / "viewer.bundle.js"
    viewer_bundle = bundle_path.read_text(encoding="utf-8")

    cycles = data.get("cycles", [])
    groups = data.get("groups", [])
    cycles_badge = f'<span class="tab-badge">{len(cycles)}</span>' if cycles else ""
    groups_badge = f'<span class="tab-badge">{len(groups)}</span>' if len(groups) > 1 else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  display: flex;
  height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", monospace;
  background: #0d1117;
  color: #e2e8f0;
  overflow: hidden;
}}

#sidebar {{
  width: 220px;
  min-width: 220px;
  background: #161b22;
  border-right: 1px solid #30363d;
  display: flex;
  flex-direction: column;
  padding: 12px;
  gap: 10px;
  overflow: hidden;
}}

#sidebar h1 {{
  font-size: 13px;
  font-weight: 600;
  color: #8b949e;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding-bottom: 8px;
  border-bottom: 1px solid #30363d;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}

#search {{
  width: 100%;
  padding: 6px 8px;
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 6px;
  color: #e2e8f0;
  font-size: 12px;
  outline: none;
}}
#search:focus {{ border-color: #58a6ff; }}
#search::placeholder {{ color: #484f58; }}

#node-list {{
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}}
#node-list::-webkit-scrollbar {{ width: 4px; }}
#node-list::-webkit-scrollbar-track {{ background: transparent; }}
#node-list::-webkit-scrollbar-thumb {{ background: #30363d; border-radius: 2px; }}

.node-item {{
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: background 0.1s;
  white-space: nowrap;
  overflow: hidden;
}}
.node-item:hover {{ background: #21262d; }}
.node-item.active {{ background: #1f2d3d; outline: 1px solid #58a6ff; }}
.node-item.hidden {{ display: none; }}

.node-dot {{
  width: 8px;
  height: 8px;
  border-radius: 2px;
  flex-shrink: 0;
}}

.node-name {{
  overflow: hidden;
  text-overflow: ellipsis;
}}

#legend {{
  position: fixed;
  bottom: 36px;
  right: 16px;
  background: rgba(22, 27, 34, 0.92);
  border: 1px solid #30363d;
  border-radius: 6px;
  padding: 7px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
  color: #8b949e;
  pointer-events: none;
  backdrop-filter: blur(4px);
}}
.legend-row {{
  display: flex;
  align-items: center;
  gap: 6px;
}}

#tab-container {{
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}}

#tab-bar {{
  display: flex;
  border-bottom: 1px solid #30363d;
  flex-shrink: 0;
  margin-bottom: 8px;
}}

.tab {{
  flex: 1;
  padding: 5px 4px;
  font-size: 11px;
  color: #6e7681;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  user-select: none;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  white-space: nowrap;
}}
.tab:hover {{ color: #e2e8f0; }}
.tab.active {{ color: #e2e8f0; border-bottom-color: #58a6ff; }}

.tab-badge {{
  font-size: 10px;
  background: #1d3a6e;
  color: #93c5fd;
  border-radius: 8px;
  padding: 1px 5px;
  line-height: 1.4;
}}

#panel-nodes {{
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
  gap: 8px;
}}

#panel-cycles {{
  flex: 1;
  overflow-y: auto;
  flex-direction: column;
  gap: 2px;
}}
#panel-cycles::-webkit-scrollbar {{ width: 4px; }}
#panel-cycles::-webkit-scrollbar-track {{ background: transparent; }}
#panel-cycles::-webkit-scrollbar-thumb {{ background: #30363d; border-radius: 2px; }}

.cycle-empty {{
  font-size: 12px;
  color: #484f58;
  padding: 16px 8px;
  text-align: center;
}}

.cycle-item {{
  display: flex;
  align-items: flex-start;
  min-width: 0;
  padding: 4px 8px;
  gap: 6px;
  cursor: pointer;
  border-radius: 4px;
  font-size: 11px;
  color: #8b949e;
  font-family: ui-monospace, SFMono-Regular, monospace;
}}
.cycle-item span {{
  white-space: normal;
  word-break: break-word;
  min-width: 0;
}}
.cycle-item:hover {{ background: #21262d; color: #e2e8f0; }}
.cycle-item.active {{ background: #1f2d3d; outline: 1px solid #1d4ed8; color: #60a5fa; }}
.cycle-dot {{
  width: 8px;
  height: 8px;
  border-radius: 2px;
  background: #60a5fa;
  flex-shrink: 0;
}}

#panel-groups {{
  flex: 1;
  overflow-y: auto;
  flex-direction: column;
  gap: 2px;
}}
#panel-groups::-webkit-scrollbar {{ width: 4px; }}
#panel-groups::-webkit-scrollbar-track {{ background: transparent; }}
#panel-groups::-webkit-scrollbar-thumb {{ background: #30363d; border-radius: 2px; }}

.group-item {{
  display: flex;
  align-items: flex-start;
  min-width: 0;
  padding: 4px 8px;
  gap: 6px;
  cursor: pointer;
  border-radius: 4px;
  font-size: 11px;
  color: #8b949e;
  font-family: ui-monospace, SFMono-Regular, monospace;
}}
.group-item span {{
  white-space: normal;
  word-break: break-word;
  min-width: 0;
}}
.group-item:hover {{ background: #21262d; color: #e2e8f0; }}
.group-item.active {{ background: #1f2d3d; outline: 1px solid #a78bfa; color: #c4b5fd; }}
.group-dot {{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #a78bfa;
  flex-shrink: 0;
  margin-top: 2px;
}}

#controls {{
  display: flex;
  flex-direction: column;
  gap: 6px;
  border-top: 1px solid #30363d;
  padding-top: 8px;
}}

button {{
  padding: 5px 10px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  border: 1px solid #30363d;
  background: #21262d;
  color: #e2e8f0;
  transition: background 0.1s, border-color 0.1s;
  width: 100%;
}}
button:hover {{ background: #30363d; }}
button:disabled {{ opacity: 0.4; cursor: default; }}


#tooltip {{
  position: fixed;
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 12px;
  pointer-events: none;
  z-index: 1000;
  display: none;
  max-width: 220px;
}}
#tooltip .tt-name {{ font-weight: 600; color: #e2e8f0; }}
#tooltip .tt-type {{ color: #8b949e; font-size: 11px; }}
#tooltip .tt-stat {{ color: #8b949e; font-size: 11px; margin-top: 2px; }}

#cy {{
  flex: 1;
  background: #0d1117;
}}

#status {{
  position: fixed;
  bottom: 12px;
  right: 16px;
  font-size: 11px;
  color: #484f58;
}}

#edge-legend {{
  position: fixed;
  bottom: 36px;
  left: 240px;
  background: rgba(22, 27, 34, 0.92);
  border: 1px solid #30363d;
  border-radius: 6px;
  padding: 7px 10px;
  display: none;
  flex-direction: column;
  gap: 5px;
  font-size: 11px;
  color: #8b949e;
  pointer-events: none;
  backdrop-filter: blur(4px);
}}
.edge-legend-row {{
  display: flex;
  align-items: center;
  gap: 8px;
}}
.edge-legend-swatch {{
  width: 18px;
  height: 2px;
  border-radius: 1px;
  flex-shrink: 0;
}}
</style>
</head>
<body>

<div id="sidebar">
  <h1>{title}</h1>
  <div id="tab-container">
    <div id="tab-bar">
      <div class="tab active" data-panel="panel-nodes">Nodes</div>
      <div class="tab" data-panel="panel-cycles">Cycles{cycles_badge}</div>
      <div class="tab" data-panel="panel-groups">Groups{groups_badge}</div>
    </div>
    <div id="panel-nodes">
      <input id="search" type="text" placeholder="Search nodes\u2026" autocomplete="off" spellcheck="false">
      <div id="node-list"></div>
    </div>
    <div id="panel-cycles" style="display:none"></div>
    <div id="panel-groups" style="display:none"></div>
  </div>
  <div id="controls">
    <button id="fit-btn">Fit all</button>
  </div>
</div>

<div id="cy"></div>
<div id="legend"></div>
<div id="edge-legend">
  <div class="edge-legend-row"><span class="edge-legend-swatch" style="background:#4ade80"></span>upstream</div>
  <div class="edge-legend-row"><span class="edge-legend-swatch" style="background:#60a5fa"></span>downstream</div>
  <div class="edge-legend-row"><span class="edge-legend-swatch" style="background:#f87171"></span>circular</div>
</div>
<div id="tooltip"></div>
<div id="status"></div>

<script>window.__FISHTAIL_DATA__ = {data_json};</script>
<script>{viewer_bundle}</script>
</body>
</html>
"""


def _open_in_browser(html: str) -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", encoding="utf-8", delete=False) as f:
        f.write(html)
        path = f.name
    webbrowser.open(Path(path).as_uri())


def _dependency_graph_to_inputs(
    dep_graph: DependencyGraph,
) -> tuple[dict[str, str], list[tuple[str, str]]]:
    node_subgraph: dict[str, str] = {}
    # Bases first, then components — consistent with generate_mermaid.py
    for brick in dep_graph.bricks:
        if brick.type == BrickType.BASE:
            node_subgraph[brick.name] = "bases"
    for brick in dep_graph.bricks:
        if brick.type == BrickType.COMPONENT:
            node_subgraph[brick.name] = "components"
    edges = [(edge.source, edge.target) for edge in dep_graph.edges]
    return node_subgraph, edges


def view_graph(dep_graph: DependencyGraph) -> None:
    """Open a DependencyGraph in the fishtail browser viewer."""
    node_subgraph, edges = _dependency_graph_to_inputs(dep_graph)
    data = _build_view_data(node_subgraph, edges)
    html = _generate_html(data, dep_graph.namespace)
    _open_in_browser(html)


def view_file(path: Path, title: str | None = None) -> None:
    """Open a Mermaid .mermaid file in the fishtail browser viewer."""
    text = path.read_text(encoding="utf-8")
    node_subgraph, edges_set = parse_mermaid_with_subgraphs(text)
    edges = list(edges_set)
    data = _build_view_data(node_subgraph, edges)
    html = _generate_html(data, title if title is not None else path.stem)
    _open_in_browser(html)
