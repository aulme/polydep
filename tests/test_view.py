import json
from pathlib import Path

from polydep.models import Brick, BrickType, DependencyGraph, Edge
from polydep.view import (
    _build_view_data,
    _dependency_graph_to_inputs,
    _find_cycles,
    _find_groups,
    _generate_html,
)

# --- _build_view_data ---


def test_build_view_data_assigns_palette_colors() -> None:
    node_subgraph = {"a": "bases", "b": "components"}
    edges: list[tuple[str, str]] = [("a", "b")]

    data = _build_view_data(node_subgraph, edges)

    nodes_by_id = {n["data"]["id"]: n["data"] for n in data["nodes"]}
    # bases gets palette index 0 (orange): bg=#7c2d12, border=#f97316
    assert nodes_by_id["a"]["bgColor"] == "#7c2d12"
    assert nodes_by_id["a"]["borderColor"] == "#f97316"
    # components gets palette index 1 (blue): bg=#1e3a5f, border=#60a5fa
    assert nodes_by_id["b"]["bgColor"] == "#1e3a5f"
    assert nodes_by_id["b"]["borderColor"] == "#60a5fa"


def test_build_view_data_unassigned_nodes_get_default_color() -> None:
    node_subgraph: dict[str, str] = {}
    edges: list[tuple[str, str]] = [("x", "y")]

    data = _build_view_data(node_subgraph, edges)

    nodes_by_id = {n["data"]["id"]: n["data"] for n in data["nodes"]}
    assert nodes_by_id["x"]["bgColor"] == "#1f2937"
    assert nodes_by_id["x"]["borderColor"] == "#6b7280"
    assert nodes_by_id["y"]["bgColor"] == "#1f2937"


def test_build_view_data_produces_correct_edge_ids() -> None:
    node_subgraph: dict[str, str] = {}
    edges = [("a", "b"), ("b", "c")]

    data = _build_view_data(node_subgraph, edges)

    edge_ids = {e["data"]["id"] for e in data["edges"]}
    assert edge_ids == {"a__b", "b__c"}


# --- _find_cycles ---


def test_find_cycles_empty_for_acyclic_graph() -> None:
    edges = [("a", "b"), ("b", "c")]

    cycles = _find_cycles(edges)

    assert cycles == []


def test_find_cycles_detects_simple_cycle() -> None:
    edges = [("a", "b"), ("b", "c"), ("c", "a")]

    cycles = _find_cycles(edges)

    assert len(cycles) == 1
    assert set(cycles[0]) == {"a", "b", "c"}


# --- _find_groups ---


def test_find_groups_single_component() -> None:
    edges = [("a", "b"), ("b", "c")]
    node_ids = ["a", "b", "c"]

    groups = _find_groups(edges, node_ids)

    assert len(groups) == 1
    assert sorted(groups[0]) == ["a", "b", "c"]


def test_find_groups_multiple_components() -> None:
    edges = [("a", "b"), ("c", "d")]
    node_ids = ["a", "b", "c", "d"]

    groups = _find_groups(edges, node_ids)

    assert len(groups) == 2
    # Sorted by size descending — both size 2, order may vary
    assert all(len(g) == 2 for g in groups)
    all_nodes = {n for g in groups for n in g}
    assert all_nodes == {"a", "b", "c", "d"}


def test_find_groups_isolated_nodes() -> None:
    edges: list[tuple[str, str]] = []
    node_ids = ["a", "b", "c"]

    groups = _find_groups(edges, node_ids)

    assert len(groups) == 3
    assert all(len(g) == 1 for g in groups)


# --- _dependency_graph_to_inputs ---


def test_dependency_graph_to_inputs_maps_bricks_and_edges() -> None:
    bricks = [
        Brick(name="alpha", type=BrickType.BASE, path="bases/alpha"),
        Brick(name="beta", type=BrickType.COMPONENT, path="components/beta"),
    ]
    graph = DependencyGraph(
        namespace="ns",
        bricks=bricks,
        edges=[Edge(source="alpha", target="beta")],
    )

    node_subgraph, edges = _dependency_graph_to_inputs(graph)

    assert node_subgraph["alpha"] == "bases"
    assert node_subgraph["beta"] == "components"
    assert ("alpha", "beta") in edges


# --- _generate_html ---


def test_generate_html_contains_fishtail_data_script() -> None:
    node_subgraph = {"a": "bases"}
    edges: list[tuple[str, str]] = []
    data = _build_view_data(node_subgraph, edges)

    html = _generate_html(data, "test-title")

    assert "window.__FISHTAIL_DATA__" in html
    script_start = html.index("window.__FISHTAIL_DATA__ = ") + len("window.__FISHTAIL_DATA__ = ")
    script_end = html.index(";</script>", script_start)
    parsed = json.loads(html[script_start:script_end])
    assert "nodes" in parsed
    assert "edges" in parsed


def test_generate_html_contains_viewer_bundle() -> None:
    data = _build_view_data({}, [])

    html = _generate_html(data, "title")

    # The viewer bundle is inlined — check a known marker from the bundle
    bundle_path = Path(__file__).parent.parent / "src" / "polydep" / "static" / "viewer.bundle.js"
    bundle_size = bundle_path.stat().st_size
    # HTML should be significantly larger than the bundle (bundle + template)
    assert len(html.encode()) > bundle_size


def test_generate_html_uses_title() -> None:
    data = _build_view_data({}, [])

    html = _generate_html(data, "my-diagram")

    assert "<title>my-diagram</title>" in html
    assert "<h1>my-diagram</h1>" in html
