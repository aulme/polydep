import os
import re
from collections import deque

from polydep.models import BrickType, DependencyGraph, Project, Workspace


def _compute_transitive_closure(seeds: list[str], graph: DependencyGraph) -> set[str]:
    edges_from: dict[str, list[str]] = {}
    for edge in graph.edges:
        edges_from.setdefault(edge.source, []).append(edge.target)

    closure: set[str] = set(seeds)
    queue: deque[str] = deque(seeds)
    while queue:
        current = queue.popleft()
        for neighbour in edges_from.get(current, []):
            if neighbour not in closure:
                closure.add(neighbour)
                queue.append(neighbour)
    return closure


def build_fixed_section(project: Project, graph: DependencyGraph, workspace: Workspace) -> str:
    brick_by_name = {brick.name: brick for brick in graph.bricks}
    edges_from: dict[str, list[str]] = {}
    edges_to: dict[str, list[str]] = {}
    for edge in graph.edges:
        edges_from.setdefault(edge.source, []).append(edge.target)
        edges_to.setdefault(edge.target, []).append(edge.source)

    # Find base bricks among declared bricks; fall back to all declared if none found
    bases = [
        name
        for name in project.declared_bricks
        if name in brick_by_name and brick_by_name[name].type == BrickType.BASE
    ]
    if not bases:
        bases = [name for name in project.declared_bricks if name in brick_by_name]

    closure = _compute_transitive_closure(bases, graph)

    # Direct: base bricks + their immediate 1-hop neighbours
    direct_names: set[str] = set(bases)
    for base in bases:
        direct_names.update(edges_from.get(base, []))
    direct_in_closure = sorted(name for name in closure if name in direct_names)
    transitive_in_closure = sorted(name for name in closure if name not in direct_names)

    def _brick_key(brick_name: str) -> str:
        brick = brick_by_name[brick_name]
        rel = os.path.relpath(workspace.root / brick.path, project.root)
        return rel.replace("\\", "/")

    def _brick_value(brick_name: str) -> str:
        return f"{workspace.namespace}/{brick_name}"

    lines: list[str] = []
    if direct_in_closure:
        lines.append("# direct")
        for name in direct_in_closure:
            key = _brick_key(name)
            value = _brick_value(name)
            lines.append(f'"{key}" = "{value}"')

    if transitive_in_closure:
        if lines:
            lines.append("")
        lines.append("# transitive")
        for name in transitive_in_closure:
            key = _brick_key(name)
            value = _brick_value(name)
            via_bricks = sorted(source for source in edges_to.get(name, []) if source in closure)
            via_comment = "  # via " + ", ".join(via_bricks) if via_bricks else ""
            lines.append(f'"{key}" = "{value}"{via_comment}')

    return "\n".join(lines) + "\n"


def apply_fix(pyproject_text: str, new_section: str) -> str:
    replacement = f"[tool.polylith.bricks]\n{new_section}"
    return re.sub(
        r"\[tool\.polylith\.bricks\][^\[]*",
        replacement,
        pyproject_text,
        flags=re.DOTALL,
    )
