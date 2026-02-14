from polydep.models import DependencyGraph, Edge


def find_all_paths(graph: DependencyGraph, source: str, target: str) -> list[list[Edge]]:
    if source == target:
        return []

    adjacency: dict[str, list[Edge]] = {}
    for edge in graph.edges:
        adjacency.setdefault(edge.source, []).append(edge)

    paths: list[list[Edge]] = []
    stack: list[tuple[str, list[Edge]]] = [(source, [])]

    while stack:
        node, path = stack.pop()
        for edge in adjacency.get(node, []):
            if edge.target in {e.source for e in path} | {source}:
                continue
            new_path = path + [edge]
            if edge.target == target:
                paths.append(new_path)
            else:
                stack.append((edge.target, new_path))

    paths.sort(key=len)
    return paths
