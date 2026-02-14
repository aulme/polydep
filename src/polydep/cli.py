from pathlib import Path

import click

from polydep.graph import build_dependency_graph
from polydep.mermaid import generate_mermaid
from polydep.workspace import parse_workspace


@click.group()
def main() -> None:
    pass


@main.command()
@click.option("--root", type=click.Path(exists=True, path_type=Path), default=Path("."))
def graph(root: Path) -> None:
    """Print the dependency graph as a Mermaid diagram."""
    try:
        workspace = parse_workspace(root)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    dependency_graph = build_dependency_graph(workspace)
    click.echo(generate_mermaid(dependency_graph), nl=False)
