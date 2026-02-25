from collections import deque

from polydep.models import BrickType, DependencyGraph, Project, ProjectIssues


def check_project(project: Project, graph: DependencyGraph) -> ProjectIssues:
    brick_by_name = {brick.name: brick for brick in graph.bricks}
    edges_from: dict[str, list[str]] = {}
    for edge in graph.edges:
        edges_from.setdefault(edge.source, []).append(edge.target)

    # Find base bricks among declared bricks; fall back to all declared if none found
    seeds = [
        name
        for name in project.declared_bricks
        if name in brick_by_name and brick_by_name[name].type == BrickType.BASE
    ]
    if not seeds:
        seeds = [name for name in project.declared_bricks if name in brick_by_name]

    # BFS to compute full transitive closure from seeds
    needed: set[str] = set(seeds)
    queue: deque[str] = deque(seeds)
    while queue:
        current = queue.popleft()
        for neighbour in edges_from.get(current, []):
            if neighbour not in needed:
                needed.add(neighbour)
                queue.append(neighbour)

    workspace_brick_names = {brick.name for brick in graph.bricks}
    missing = sorted(needed - project.declared_bricks)
    extra = sorted(
        name for name in project.declared_bricks - needed if name in workspace_brick_names
    )

    return ProjectIssues(project=project, missing=missing, extra=extra)
