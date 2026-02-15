from pathlib import Path

from polydep.generate_mermaid import generate_mermaid
from polydep.graph import build_dependency_graph
from polydep.models import (
    Brick,
    BrickType,
    DependencyGraph,
    Edge,
)
from polydep.workspace import parse_workspace


def _make_graph(
    bricks: list[Brick] | None = None,
    edges: list[Edge] | None = None,
    namespace: str = "ns",
) -> DependencyGraph:
    return DependencyGraph(namespace=namespace, bricks=bricks or [], edges=edges or [])


def _make_brick(name: str, brick_type: BrickType = BrickType.COMPONENT) -> Brick:
    return Brick(name=name, type=brick_type, path=f"fake/{name}")


# --- Unit tests ---


def test_generate_mermaid_empty_graph() -> None:
    graph = _make_graph()

    result = generate_mermaid(graph)

    assert result == "graph LR\n"


def test_generate_mermaid_single_edge() -> None:
    graph = _make_graph(
        bricks=[
            _make_brick("api", BrickType.BASE),
            _make_brick("log"),
        ],
        edges=[Edge(source="api", target="log")],
    )

    result = generate_mermaid(graph)

    assert result == (
        "graph LR\n"
        "  subgraph bases\n"
        "    api\n"
        "  end\n"
        "  subgraph components\n"
        "    log\n"
        "  end\n"
        "  api --> log\n"
    )


def test_generate_mermaid_components_only() -> None:
    graph = _make_graph(
        bricks=[
            _make_brick("a"),
            _make_brick("b"),
        ],
        edges=[Edge(source="a", target="b")],
    )

    result = generate_mermaid(graph)

    assert result == ("graph LR\n  subgraph components\n    a\n    b\n  end\n  a --> b\n")


def test_generate_mermaid_bases_only() -> None:
    graph = _make_graph(
        bricks=[
            _make_brick("x", BrickType.BASE),
            _make_brick("y", BrickType.BASE),
        ],
        edges=[Edge(source="x", target="y")],
    )

    result = generate_mermaid(graph)

    assert result == ("graph LR\n  subgraph bases\n    x\n    y\n  end\n  x --> y\n")


def test_generate_mermaid_sorts_bricks_alphabetically() -> None:
    graph = _make_graph(
        bricks=[
            _make_brick("zebra"),
            _make_brick("apple"),
            _make_brick("mango"),
        ],
    )

    result = generate_mermaid(graph)

    assert result == ("graph LR\n  subgraph components\n    apple\n    mango\n    zebra\n  end\n")


def test_generate_mermaid_sorts_edges() -> None:
    graph = _make_graph(
        bricks=[
            _make_brick("a"),
            _make_brick("b"),
            _make_brick("c"),
        ],
        edges=[
            Edge(source="c", target="a"),
            Edge(source="a", target="b"),
        ],
    )

    result = generate_mermaid(graph)

    assert result == (
        "graph LR\n  subgraph components\n    a\n    b\n    c\n  end\n  a --> b\n  c --> a\n"
    )


def test_generate_mermaid_leaf_brick_appears_in_subgraph() -> None:
    """A brick with no edges still appears in its subgraph."""
    graph = _make_graph(
        bricks=[
            _make_brick("api", BrickType.BASE),
            _make_brick("db"),
            _make_brick("log"),
        ],
        edges=[Edge(source="api", target="log")],
    )

    result = generate_mermaid(graph)

    assert "    db\n" in result
    assert "    log\n" in result


# --- Integration test ---


def test_generate_mermaid_sample_project(sample_project: Path) -> None:
    workspace = parse_workspace(sample_project)
    graph = build_dependency_graph(workspace)

    result = generate_mermaid(graph)

    assert result == (
        "graph LR\n"
        "  subgraph bases\n"
        "    consumer\n"
        "    greet_api\n"
        "    message_api\n"
        "  end\n"
        "  subgraph components\n"
        "    database\n"
        "    dictionaries\n"
        "    greeting\n"
        "    kafka\n"
        "    log\n"
        "    message\n"
        "    schema\n"
        "  end\n"
        "  consumer --> kafka\n"
        "  consumer --> log\n"
        "  greet_api --> greeting\n"
        "  greet_api --> log\n"
        "  kafka --> log\n"
        "  message --> database\n"
        "  message --> dictionaries\n"
        "  message --> kafka\n"
        "  message --> schema\n"
        "  message_api --> database\n"
        "  message_api --> log\n"
        "  message_api --> message\n"
        "  message_api --> schema\n"
    )
