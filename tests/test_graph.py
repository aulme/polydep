from pathlib import Path

from polydep.graph import build_dependency_graph
from polydep.models import (
    Brick,
    BrickType,
    Import,
    SourceFile,
    Workspace,
)
from polydep.workspace import parse_workspace

SAMPLE_PROJECT = Path(__file__).resolve().parent.parent / "sample_project"


# --- Helpers for constructing test workspaces in memory ---


def _make_workspace(namespace: str, bricks: tuple[Brick, ...]) -> Workspace:
    return Workspace(namespace=namespace, root=Path("/fake"), bricks=bricks)


def _make_brick(
    name: str,
    namespace: str,
    imports: tuple[Import, ...] = (),
    brick_type: BrickType = BrickType.COMPONENT,
) -> Brick:
    return Brick(
        name=name,
        type=brick_type,
        path=f"components/{namespace}/{name}",
        files=(SourceFile(path=f"components/{namespace}/{name}/core.py", imports=imports),),
    )


# --- Unit tests with constructed workspaces ---


def test_build_dependency_graph_simple_edge() -> None:
    workspace = _make_workspace(
        "ns",
        (
            _make_brick("a", "ns", imports=(Import(module="ns.b", line=1, statement="from ns import b"),)),
            _make_brick("b", "ns"),
        ),
    )

    graph = build_dependency_graph(workspace)

    edge_set = {(edge.source, edge.target) for edge in graph.edges}
    assert edge_set == {("a", "b")}


def test_build_dependency_graph_excludes_stdlib_imports() -> None:
    workspace = _make_workspace(
        "ns",
        (
            _make_brick(
                "a",
                "ns",
                imports=(
                    Import(module="json", line=1, statement="import json"),
                    Import(module="os.path", line=2, statement="import os.path"),
                ),
            ),
        ),
    )

    graph = build_dependency_graph(workspace)

    assert graph.edges == ()


def test_build_dependency_graph_excludes_unknown_namespace_imports() -> None:
    """Imports under the namespace but not matching any brick are excluded."""
    workspace = _make_workspace(
        "ns",
        (
            _make_brick(
                "a",
                "ns",
                imports=(Import(module="ns.nonexistent", line=1, statement="from ns import nonexistent"),),
            ),
        ),
    )

    graph = build_dependency_graph(workspace)

    assert graph.edges == ()


def test_build_dependency_graph_deduplicates_edges() -> None:
    """Multiple imports from the same brick to the same target produce one edge."""
    workspace = _make_workspace(
        "ns",
        (
            _make_brick(
                "a",
                "ns",
                imports=(
                    Import(module="ns.b", line=1, statement="from ns import b"),
                    Import(module="ns.b.util", line=2, statement="from ns.b.util import helper"),
                ),
            ),
            _make_brick("b", "ns"),
        ),
    )

    graph = build_dependency_graph(workspace)

    edge_set = {(edge.source, edge.target) for edge in graph.edges}
    assert edge_set == {("a", "b")}


def test_build_dependency_graph_self_import_excluded() -> None:
    workspace = _make_workspace(
        "ns",
        (
            _make_brick(
                "a",
                "ns",
                imports=(Import(module="ns.a", line=1, statement="from ns.a import something"),),
            ),
        ),
    )

    graph = build_dependency_graph(workspace)

    assert graph.edges == ()


def test_build_dependency_graph_empty_workspace() -> None:
    workspace = _make_workspace("ns", ())

    graph = build_dependency_graph(workspace)

    assert graph.bricks == ()
    assert graph.edges == ()


def test_build_dependency_graph_deep_submodule_resolves_to_brick() -> None:
    """An import like ns.b.sub.module should resolve to brick b."""
    workspace = _make_workspace(
        "ns",
        (
            _make_brick(
                "a",
                "ns",
                imports=(
                    Import(module="ns.b.sub.module", line=1, statement="from ns.b.sub.module import thing"),
                ),
            ),
            _make_brick("b", "ns"),
        ),
    )

    graph = build_dependency_graph(workspace)

    edge_set = {(edge.source, edge.target) for edge in graph.edges}
    assert edge_set == {("a", "b")}


def test_build_dependency_graph_multiple_bricks_with_shared_dependency() -> None:
    """Two bricks both depending on the same third brick."""
    workspace = _make_workspace(
        "ns",
        (
            _make_brick("a", "ns", imports=(Import(module="ns.c", line=1, statement="from ns import c"),)),
            _make_brick("b", "ns", imports=(Import(module="ns.c", line=1, statement="from ns import c"),)),
            _make_brick("c", "ns"),
        ),
    )

    graph = build_dependency_graph(workspace)

    edge_set = {(edge.source, edge.target) for edge in graph.edges}
    assert edge_set == {("a", "c"), ("b", "c")}


# --- Integration tests using sample_project ---


def test_build_dependency_graph_contains_all_bricks() -> None:
    workspace = parse_workspace(SAMPLE_PROJECT)

    graph = build_dependency_graph(workspace)

    brick_names = {brick.name for brick in graph.bricks}
    assert brick_names == {
        "database",
        "dictionaries",
        "greeting",
        "kafka",
        "log",
        "message",
        "schema",
        "greet_api",
        "consumer",
        "message_api",
    }


def test_build_dependency_graph_preserves_namespace() -> None:
    workspace = parse_workspace(SAMPLE_PROJECT)

    graph = build_dependency_graph(workspace)

    assert graph.namespace == "example"


def test_build_dependency_graph_has_expected_edges() -> None:
    workspace = parse_workspace(SAMPLE_PROJECT)

    graph = build_dependency_graph(workspace)

    edge_set = {(edge.source, edge.target) for edge in graph.edges}
    assert edge_set == {
        ("greet_api", "greeting"),
        ("greet_api", "log"),
        ("consumer", "kafka"),
        ("consumer", "log"),
        ("message_api", "log"),
        ("message_api", "message"),
        ("message_api", "database"),
        ("message_api", "schema"),
        ("kafka", "log"),
        ("message", "kafka"),
        ("message", "database"),
        ("message", "dictionaries"),
        ("message", "schema"),
    }


def test_build_dependency_graph_leaf_bricks_have_no_outgoing_edges() -> None:
    workspace = parse_workspace(SAMPLE_PROJECT)

    graph = build_dependency_graph(workspace)

    sources = {edge.source for edge in graph.edges}
    leaf_bricks = {"greeting", "log", "database", "schema", "dictionaries"}
    assert sources & leaf_bricks == set()


def test_build_dependency_graph_excludes_self_imports() -> None:
    workspace = parse_workspace(SAMPLE_PROJECT)

    graph = build_dependency_graph(workspace)

    for edge in graph.edges:
        assert edge.source != edge.target, f"Self-edge found: {edge.source} → {edge.target}"
