from pathlib import Path

from polydep.generate_mermaid import generate_mermaid
from polydep.graph import build_dependency_graph
from polydep.parse_mermaid import parse_mermaid
from polydep.workspace import parse_workspace

# --- Unit tests ---


def test_parse_mermaid_simple_edges() -> None:
    content = "graph LR\n  a --> b\n  b --> c\n"

    edges = parse_mermaid(content)

    assert edges == {("a", "b"), ("b", "c")}


def test_parse_mermaid_with_subgraphs() -> None:
    content = (
        "graph LR\n"
        "  subgraph bases\n"
        "    api\n"
        "  end\n"
        "  subgraph components\n"
        "    log\n"
        "  end\n"
        "  api --> log\n"
    )

    edges = parse_mermaid(content)

    assert edges == {("api", "log")}


def test_parse_mermaid_ignores_comments() -> None:
    content = "graph LR\n  %% this is a comment\n  a --> b\n"

    edges = parse_mermaid(content)

    assert edges == {("a", "b")}


def test_parse_mermaid_different_arrow_styles() -> None:
    content = "graph LR\n  a --> b\n  c --- d\n  e ==> f\n  g -.-> h\n"

    edges = parse_mermaid(content)

    assert edges == {("a", "b"), ("c", "d"), ("e", "f"), ("g", "h")}


def test_parse_mermaid_link_text() -> None:
    content = "graph LR\n  a -->|depends on| b\n"

    edges = parse_mermaid(content)

    assert edges == {("a", "b")}


def test_parse_mermaid_node_labels() -> None:
    content = "graph LR\n  api[API Service] --> db[Database]\n"

    edges = parse_mermaid(content)

    assert edges == {("api", "db")}


def test_parse_mermaid_ignores_styling() -> None:
    content = (
        "graph LR\n"
        "  a --> b\n"
        "  style a fill:#f9f\n"
        "  classDef default fill:#fff\n"
        "  class a,b default\n"
    )

    edges = parse_mermaid(content)

    assert edges == {("a", "b")}


# --- Integration test ---


def test_parse_mermaid_round_trip(sample_project: Path) -> None:
    """Parsing the output of generate_mermaid recovers the same edges."""
    workspace = parse_workspace(sample_project)
    graph = build_dependency_graph(workspace)
    mermaid = generate_mermaid(graph)

    edges = parse_mermaid(mermaid)

    expected = {(e.source, e.target) for e in graph.edges}
    assert edges == expected
