from pathlib import Path

from polydep.graph import build_dependency_graph
from polydep.models import (
    Brick,
    BrickType,
    DependencyGraph,
    Edge,
)
from polydep.paths import find_all_paths
from polydep.workspace import parse_workspace


def _make_graph(edges: list[tuple[str, str]]) -> DependencyGraph:
    """Build a DependencyGraph from a list of (source, target) pairs."""
    brick_names: set[str] = set()
    for source, target in edges:
        brick_names.add(source)
        brick_names.add(target)
    bricks = [
        Brick(name=name, type=BrickType.COMPONENT, path=f"fake/{name}")
        for name in sorted(brick_names)
    ]
    return DependencyGraph(
        namespace="ns",
        bricks=bricks,
        edges=[Edge(source=source, target=target) for source, target in edges],
    )


def _path_nodes(path: list[Edge]) -> list[str]:
    """Extract the brick-name chain from a list of edges."""
    if not path:
        return []
    return [path[0].source] + [edge.target for edge in path]


# --- Unit tests ---


def test_find_all_paths_direct() -> None:
    graph = _make_graph([("a", "b")])

    paths = find_all_paths(graph, "a", "b")

    assert [_path_nodes(p) for p in paths] == [["a", "b"]]


def test_find_all_paths_transitive() -> None:
    graph = _make_graph([("a", "b"), ("b", "c")])

    paths = find_all_paths(graph, "a", "c")

    assert [_path_nodes(p) for p in paths] == [["a", "b", "c"]]


def test_find_all_paths_multiple_paths_sorted_by_length() -> None:
    graph = _make_graph([("a", "b"), ("b", "c"), ("a", "c")])

    paths = find_all_paths(graph, "a", "c")

    assert [_path_nodes(p) for p in paths] == [["a", "c"], ["a", "b", "c"]]


def test_find_all_paths_no_path() -> None:
    graph = _make_graph([("a", "b"), ("c", "d")])

    paths = find_all_paths(graph, "a", "d")

    assert paths == []


def test_find_all_paths_same_source_and_target() -> None:
    graph = _make_graph([("a", "b")])

    paths = find_all_paths(graph, "a", "a")

    assert paths == []


def test_find_all_paths_handles_cycle() -> None:
    graph = _make_graph([("a", "b"), ("b", "c"), ("c", "a")])

    paths = find_all_paths(graph, "a", "c")

    assert [_path_nodes(p) for p in paths] == [["a", "b", "c"]]


def test_find_all_paths_diamond() -> None:
    """A diamond: a->b, a->c, b->d, c->d produces two equal-length paths."""
    graph = _make_graph([("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")])

    paths = find_all_paths(graph, "a", "d")

    node_paths = [_path_nodes(p) for p in paths]
    assert len(node_paths) == 2
    assert ["a", "b", "d"] in node_paths
    assert ["a", "c", "d"] in node_paths


def test_find_all_paths_returns_edge_objects() -> None:
    """Each path element is an Edge from the graph, not a copy."""
    graph = _make_graph([("a", "b"), ("b", "c")])

    paths = find_all_paths(graph, "a", "c")

    assert len(paths) == 1
    assert all(isinstance(edge, Edge) for edge in paths[0])
    assert paths[0][0].source == "a"
    assert paths[0][0].target == "b"
    assert paths[0][1].source == "b"
    assert paths[0][1].target == "c"


# --- Integration tests using sample_project ---


def test_find_all_paths_direct_dependency(sample_project: Path) -> None:
    workspace = parse_workspace(sample_project)
    graph = build_dependency_graph(workspace)

    paths = find_all_paths(graph, "greet_api", "greeting")

    assert [_path_nodes(p) for p in paths] == [["greet_api", "greeting"]]


def test_find_all_paths_direct_and_transitive(sample_project: Path) -> None:
    workspace = parse_workspace(sample_project)
    graph = build_dependency_graph(workspace)

    paths = find_all_paths(graph, "consumer", "log")

    assert [_path_nodes(p) for p in paths] == [["consumer", "log"], ["consumer", "kafka", "log"]]


def test_find_all_paths_no_dependency(sample_project: Path) -> None:
    workspace = parse_workspace(sample_project)
    graph = build_dependency_graph(workspace)

    paths = find_all_paths(graph, "greet_api", "database")

    assert paths == []


def test_find_all_paths_transitive_only(sample_project: Path) -> None:
    workspace = parse_workspace(sample_project)
    graph = build_dependency_graph(workspace)

    paths = find_all_paths(graph, "message", "log")

    assert [_path_nodes(p) for p in paths] == [["message", "kafka", "log"]]


def test_find_all_paths_carries_import_provenance(sample_project: Path) -> None:
    """Each edge in a path carries the file and line info for the imports that cause it."""
    workspace = parse_workspace(sample_project)
    graph = build_dependency_graph(workspace)

    paths = find_all_paths(graph, "greet_api", "greeting")

    assert len(paths) == 1
    edge = paths[0][0]
    assert edge.source == "greet_api"
    assert edge.target == "greeting"
    assert len(edge.imports) >= 1
    assert edge.imports[0].file == "bases/example/greet_api/core.py"
    assert edge.imports[0].line == 3
    assert edge.imports[0].statement == "from example import greeting"
