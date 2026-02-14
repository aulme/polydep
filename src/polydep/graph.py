from polydep.models import DependencyGraph, Edge, Import, Workspace


def _resolve_brick_name(import_: Import, namespace: str) -> str | None:
    """Extract the brick name from an import module, or None if it's not under the namespace."""
    prefix = namespace + "."
    if not import_.module.startswith(prefix):
        return None
    # "example.database.message.crud" → "database"
    rest = import_.module[len(prefix) :]
    return rest.split(".")[0]


def build_dependency_graph(workspace: Workspace) -> DependencyGraph:
    brick_names = {brick.name for brick in workspace.bricks}
    seen: set[tuple[str, str]] = set()

    for brick in workspace.bricks:
        for source_file in brick.files:
            for import_ in source_file.imports:
                target = _resolve_brick_name(import_, workspace.namespace)
                if target is None or target not in brick_names or target == brick.name:
                    continue
                seen.add((brick.name, target))

    edges = tuple(Edge(source=source, target=target) for source, target in sorted(seen))
    return DependencyGraph(namespace=workspace.namespace, bricks=workspace.bricks, edges=edges)
