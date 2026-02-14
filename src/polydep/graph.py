from collections import defaultdict

from polydep.models import DependencyGraph, Edge, Import, ImportLocation, Workspace


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
    edge_imports: dict[tuple[str, str], list[ImportLocation]] = defaultdict(list)

    for brick in workspace.bricks:
        for source_file in brick.files:
            for import_ in source_file.imports:
                target = _resolve_brick_name(import_, workspace.namespace)
                if target is None or target not in brick_names or target == brick.name:
                    continue
                edge_imports[(brick.name, target)].append(
                    ImportLocation(
                        file=source_file.path,
                        line=import_.line,
                        statement=import_.statement,
                    )
                )

    edges = [
        Edge(source=source, target=target, imports=edge_imports[(source, target)])
        for source, target in sorted(edge_imports)
    ]
    return DependencyGraph(namespace=workspace.namespace, bricks=workspace.bricks, edges=edges)
