from polydep.models import BrickType, DependencyGraph


def generate_mermaid(graph: DependencyGraph) -> str:
    lines = ["graph LR"]

    bases = sorted(brick.name for brick in graph.bricks if brick.type == BrickType.BASE)
    components = sorted(brick.name for brick in graph.bricks if brick.type == BrickType.COMPONENT)

    for label, names in (("bases", bases), ("components", components)):
        if names:
            lines.append(f"  subgraph {label}")
            for name in names:
                lines.append(f"    {name}")
            lines.append("  end")

    for edge in sorted(graph.edges, key=lambda edge: (edge.source, edge.target)):
        lines.append(f"  {edge.source} --> {edge.target}")

    return "\n".join(lines) + "\n"
