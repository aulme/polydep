from pathlib import Path

import click

from polydep.generate_mermaid import generate_mermaid
from polydep.graph import build_dependency_graph
from polydep.models import Edge
from polydep.parse_mermaid import parse_mermaid
from polydep.paths import find_all_paths
from polydep.workspace import parse_workspace


@click.group()
def main() -> None:
    pass


@main.command()
@click.option("--root", type=click.Path(exists=True, path_type=Path), default=Path("."))
@click.option("--save", is_flag=True, help="Save to polydep.expected.mermaid instead of printing.")
def graph(root: Path, save: bool) -> None:
    """Print the dependency graph as a Mermaid diagram."""
    try:
        workspace = parse_workspace(root)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    dependency_graph = build_dependency_graph(workspace)
    output = generate_mermaid(dependency_graph)
    if save:
        Path("polydep.expected.mermaid").write_text(output)
    else:
        click.echo(output, nl=False)


def _format_path(index: int, path: list[Edge]) -> str:
    length = len(path)
    if length == 1:
        label = f"Path {index} (direct):"
    else:
        label = f"Path {index} (transitive, length {length}):"

    chain = " -> ".join([path[0].source] + [edge.target for edge in path])
    imports = sorted(
        (location.file, location.line, location.statement)
        for edge in path
        for location in edge.imports
    )
    provenance_lines = [f"    {file}:{line}  {statement}" for file, line, statement in imports]

    return "\n".join([label, f"  {chain}"] + provenance_lines)


@main.command()
@click.argument("source")
@click.argument("target")
@click.option("--root", type=click.Path(exists=True, path_type=Path), default=Path("."))
def why(source: str, target: str, root: Path) -> None:
    """Explain why one brick depends on another."""
    try:
        workspace = parse_workspace(root)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc

    dependency_graph = build_dependency_graph(workspace)
    brick_names = {brick.name for brick in dependency_graph.bricks}

    for name in (source, target):
        if name not in brick_names:
            available = ", ".join(sorted(brick_names))
            raise click.ClickException(f"Brick '{name}' not found. Available bricks: {available}")

    paths = find_all_paths(dependency_graph, source, target)

    if not paths:
        click.echo(f"{source} does not depend on {target}.")
        return

    count = len(paths)
    click.echo(f"{source} depends on {target} via {count} path{'s' if count != 1 else ''}:")
    for index, path in enumerate(paths, start=1):
        click.echo()
        click.echo(_format_path(index, path))


_DEFAULT_EXPECTED_FILE = "polydep.expected.mermaid"


@main.command()
@click.option(
    "--expected",
    type=click.Path(path_type=Path),
    default=Path(_DEFAULT_EXPECTED_FILE),
    help=f"Path to expected graph file (default: {_DEFAULT_EXPECTED_FILE}).",
)
@click.option("--root", type=click.Path(exists=True, path_type=Path), default=Path("."))
def check(expected: Path, root: Path) -> None:
    """Compare actual dependencies against an expected graph file."""
    if not expected.exists():
        raise click.ClickException(f"{expected} not found.")

    try:
        workspace = parse_workspace(root)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc

    dependency_graph = build_dependency_graph(workspace)
    actual_edges = {(edge.source, edge.target): edge for edge in dependency_graph.edges}
    expected_edges = parse_mermaid(expected.read_text())

    unexpected = sorted(actual_edges.keys() - expected_edges)
    missing = sorted(expected_edges - actual_edges.keys())

    if not unexpected and not missing:
        click.echo("Check passed.")
        return

    click.echo("Check failed.")

    if unexpected:
        click.echo()
        click.echo("Unexpected dependencies:")
        for source, target in unexpected:
            click.echo(f"  {source} --> {target}")
            edge = actual_edges[(source, target)]
            for location in sorted(edge.imports, key=lambda l: (l.file, l.line)):
                click.echo(f"    {location.file}:{location.line}  {location.statement}")

    if missing:
        click.echo()
        click.echo("Missing dependencies:")
        for source, target in missing:
            click.echo(f"  {source} --> {target}")

    raise SystemExit(1)
