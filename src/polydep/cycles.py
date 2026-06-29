import json


def find_cycles(edges: list[tuple[str, str]]) -> list[list[str]]:
    """Find all simple cycles in a directed graph.

    Each cycle is returned as a canonical node list (rotated to start at its
    lexicographically smallest node); ``a -> b -> a`` is ``["a", "b"]`` and a
    self-loop is ``["a"]``. Cycles are deduplicated and sorted by length then
    name. Port of findSimpleCycles from fishtail/src/generate-html.ts.
    """
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


def format_cycle(cycle: list[str]) -> str:
    """Render a cycle as a closed loop: ``["a", "b"]`` -> ``"a -> b -> a"``."""
    return " -> ".join([*cycle, cycle[0]])
