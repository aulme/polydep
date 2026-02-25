from pathlib import Path

from polydep.models import Brick, BrickType, DependencyGraph, Edge, Project, Workspace
from polydep.project_fixer import apply_fix, build_fixed_section


def _make_workspace(root: Path, bricks: list[Brick]) -> Workspace:
    return Workspace(namespace="example", root=root, bricks=bricks)


def _make_project(root: Path, project_name: str, declared: set[str]) -> Project:
    project_dir = root / "projects" / project_name
    return Project(
        name=project_name,
        root=project_dir,
        pyproject_path=project_dir / "pyproject.toml",
        declared_bricks=declared,
    )


def _make_graph(bricks: list[Brick], edges: list[tuple[str, str]]) -> DependencyGraph:
    graph_edges = [Edge(source=source, target=target) for source, target in edges]
    return DependencyGraph(namespace="example", bricks=bricks, edges=graph_edges)


def test_build_fixed_section_no_transitive(tmp_path: Path) -> None:
    bricks = [
        Brick(name="consumer", type=BrickType.BASE, path="bases/example/consumer"),
        Brick(name="kafka", type=BrickType.COMPONENT, path="components/example/kafka"),
        Brick(name="log", type=BrickType.COMPONENT, path="components/example/log"),
    ]
    workspace = _make_workspace(tmp_path, bricks)
    project = _make_project(tmp_path, "consumer_app", {"consumer", "kafka", "log"})
    graph = _make_graph(bricks, [("consumer", "kafka"), ("consumer", "log"), ("kafka", "log")])

    result = build_fixed_section(project, graph, workspace)

    assert "# direct" in result
    assert "# transitive" not in result
    assert '"../../bases/example/consumer" = "example/consumer"' in result
    assert '"../../components/example/kafka" = "example/kafka"' in result
    assert '"../../components/example/log" = "example/log"' in result


def test_build_fixed_section_with_transitive(tmp_path: Path) -> None:
    bricks = [
        Brick(name="message_api", type=BrickType.BASE, path="bases/example/message_api"),
        Brick(name="database", type=BrickType.COMPONENT, path="components/example/database"),
        Brick(
            name="dictionaries",
            type=BrickType.COMPONENT,
            path="components/example/dictionaries",
        ),
        Brick(name="kafka", type=BrickType.COMPONENT, path="components/example/kafka"),
        Brick(name="log", type=BrickType.COMPONENT, path="components/example/log"),
        Brick(name="message", type=BrickType.COMPONENT, path="components/example/message"),
        Brick(name="schema", type=BrickType.COMPONENT, path="components/example/schema"),
    ]
    workspace = _make_workspace(tmp_path, bricks)
    project = _make_project(
        tmp_path,
        "messaging",
        {"message_api", "database", "dictionaries", "kafka", "log", "message", "schema"},
    )
    graph = _make_graph(
        bricks,
        [
            ("message_api", "database"),
            ("message_api", "log"),
            ("message_api", "message"),
            ("message_api", "schema"),
            ("message", "database"),
            ("message", "dictionaries"),
            ("message", "kafka"),
            ("message", "schema"),
            ("kafka", "log"),
        ],
    )

    result = build_fixed_section(project, graph, workspace)

    assert "# direct" in result
    assert "# transitive" in result
    # Direct bricks (message_api + its 1-hop neighbours)
    assert '"../../bases/example/message_api" = "example/message_api"' in result
    assert '"../../components/example/database" = "example/database"' in result
    assert '"../../components/example/log" = "example/log"' in result
    assert '"../../components/example/message" = "example/message"' in result
    assert '"../../components/example/schema" = "example/schema"' in result
    # Transitive bricks with via annotation
    assert (
        '"../../components/example/dictionaries" = "example/dictionaries"  # via message' in result
    )
    assert '"../../components/example/kafka" = "example/kafka"  # via message' in result


def test_build_fixed_section_direct_block_comes_before_transitive(tmp_path: Path) -> None:
    bricks = [
        Brick(name="message_api", type=BrickType.BASE, path="bases/example/message_api"),
        Brick(name="message", type=BrickType.COMPONENT, path="components/example/message"),
        Brick(name="kafka", type=BrickType.COMPONENT, path="components/example/kafka"),
    ]
    workspace = _make_workspace(tmp_path, bricks)
    project = _make_project(tmp_path, "messaging", {"message_api", "message", "kafka"})
    graph = _make_graph(bricks, [("message_api", "message"), ("message", "kafka")])

    result = build_fixed_section(project, graph, workspace)

    direct_pos = result.index("# direct")
    transitive_pos = result.index("# transitive")
    assert direct_pos < transitive_pos


def test_build_fixed_section_via_includes_only_closure_members(tmp_path: Path) -> None:
    """Bricks outside the project closure are not listed in 'via' annotations."""
    bricks = [
        Brick(name="message_api", type=BrickType.BASE, path="bases/example/message_api"),
        Brick(name="consumer", type=BrickType.BASE, path="bases/example/consumer"),
        Brick(name="kafka", type=BrickType.COMPONENT, path="components/example/kafka"),
        Brick(name="message", type=BrickType.COMPONENT, path="components/example/message"),
    ]
    workspace = _make_workspace(tmp_path, bricks)
    # Only message_api project — consumer is outside this project's closure
    project = _make_project(tmp_path, "messaging", {"message_api", "message", "kafka"})
    graph = _make_graph(
        bricks,
        [
            ("message_api", "message"),
            ("consumer", "kafka"),  # consumer imports kafka but consumer is not in closure
            ("message", "kafka"),
        ],
    )

    result = build_fixed_section(project, graph, workspace)

    # kafka is transitive via message only, not consumer (consumer not in closure)
    assert "# via message" in result
    assert "consumer" not in result.split("# via")[-1]


def test_apply_fix_replaces_bricks_section(tmp_path: Path) -> None:
    original = (
        "[build-system]\n"
        'requires = ["hatchling"]\n'
        "\n"
        "[tool.polylith.bricks]\n"
        '"../../bases/example/consumer" = "example/consumer"\n'
        '"../../components/example/kafka" = "example/kafka"\n"'
    )
    new_section = (
        "# direct\n"
        '"../../bases/example/consumer" = "example/consumer"\n'
        '"../../components/example/kafka" = "example/kafka"\n'
        '"../../components/example/log" = "example/log"\n'
    )

    result = apply_fix(original, new_section)

    assert "[tool.polylith.bricks]\n" + new_section in result
    assert "[build-system]" in result


def test_apply_fix_preserves_content_before_bricks_section() -> None:
    original = (
        "[project]\n"
        'name = "my_app"\n'
        "\n"
        "[tool.polylith.bricks]\n"
        '"../../components/example/log" = "example/log"\n'
    )
    new_section = '"../../components/example/other" = "example/other"\n'

    result = apply_fix(original, new_section)

    assert result.startswith("[project]\n")
    assert '[tool.polylith.bricks]\n"../../components/example/other"' in result
    assert "log" not in result
