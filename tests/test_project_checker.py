from pathlib import Path

from polydep.models import Brick, BrickType, DependencyGraph, Edge, Project
from polydep.project_checker import check_project


def _make_project(tmp_path: Path, name: str, declared: set[str]) -> Project:
    return Project(
        name=name,
        root=tmp_path / "projects" / name,
        pyproject_path=tmp_path / "projects" / name / "pyproject.toml",
        declared_bricks=declared,
    )


def _make_graph(bricks: list[Brick], edges: list[tuple[str, str]]) -> DependencyGraph:
    graph_edges = [Edge(source=source, target=target) for source, target in edges]
    return DependencyGraph(namespace="example", bricks=bricks, edges=graph_edges)


def test_check_project_missing_brick(tmp_path: Path) -> None:
    bricks = [
        Brick(name="consumer", type=BrickType.BASE, path="bases/example/consumer"),
        Brick(name="kafka", type=BrickType.COMPONENT, path="components/example/kafka"),
        Brick(name="log", type=BrickType.COMPONENT, path="components/example/log"),
    ]
    graph = _make_graph(bricks, [("consumer", "kafka"), ("consumer", "log"), ("kafka", "log")])
    project = _make_project(tmp_path, "consumer_app", {"consumer", "kafka"})

    issues = check_project(project, graph)

    assert issues.missing == ["log"]
    assert issues.extra == []


def test_check_project_extra_brick(tmp_path: Path) -> None:
    bricks = [
        Brick(name="consumer", type=BrickType.BASE, path="bases/example/consumer"),
        Brick(name="kafka", type=BrickType.COMPONENT, path="components/example/kafka"),
        Brick(name="log", type=BrickType.COMPONENT, path="components/example/log"),
        Brick(name="greeting", type=BrickType.COMPONENT, path="components/example/greeting"),
    ]
    graph = _make_graph(bricks, [("consumer", "kafka"), ("consumer", "log"), ("kafka", "log")])
    project = _make_project(tmp_path, "consumer_app", {"consumer", "kafka", "log", "greeting"})

    issues = check_project(project, graph)

    assert issues.missing == []
    assert issues.extra == ["greeting"]


def test_check_project_missing_and_extra(tmp_path: Path) -> None:
    bricks = [
        Brick(name="consumer", type=BrickType.BASE, path="bases/example/consumer"),
        Brick(name="kafka", type=BrickType.COMPONENT, path="components/example/kafka"),
        Brick(name="log", type=BrickType.COMPONENT, path="components/example/log"),
        Brick(name="greeting", type=BrickType.COMPONENT, path="components/example/greeting"),
    ]
    graph = _make_graph(bricks, [("consumer", "kafka"), ("consumer", "log"), ("kafka", "log")])
    # Missing log, has extra greeting
    project = _make_project(tmp_path, "consumer_app", {"consumer", "kafka", "greeting"})

    issues = check_project(project, graph)

    assert issues.missing == ["log"]
    assert issues.extra == ["greeting"]


def test_check_project_ok(tmp_path: Path) -> None:
    bricks = [
        Brick(name="consumer", type=BrickType.BASE, path="bases/example/consumer"),
        Brick(name="kafka", type=BrickType.COMPONENT, path="components/example/kafka"),
        Brick(name="log", type=BrickType.COMPONENT, path="components/example/log"),
    ]
    graph = _make_graph(bricks, [("consumer", "kafka"), ("consumer", "log"), ("kafka", "log")])
    project = _make_project(tmp_path, "consumer_app", {"consumer", "kafka", "log"})

    issues = check_project(project, graph)

    assert issues.missing == []
    assert issues.extra == []


def test_check_project_transitive_included(tmp_path: Path) -> None:
    # message_api → database, log, message, schema; message → database, dictionaries, kafka, schema
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
    project = _make_project(
        tmp_path,
        "messaging",
        {"message_api", "database", "dictionaries", "kafka", "log", "message", "schema"},
    )

    issues = check_project(project, graph)

    assert issues.missing == []
    assert issues.extra == []


def test_check_project_unknown_declared_bricks_ignored(tmp_path: Path) -> None:
    """Bricks declared in pyproject.toml that don't exist in the workspace are silently ignored."""
    bricks = [
        Brick(name="consumer", type=BrickType.BASE, path="bases/example/consumer"),
        Brick(name="log", type=BrickType.COMPONENT, path="components/example/log"),
    ]
    graph = _make_graph(bricks, [("consumer", "log")])
    # "phantom" is not a real workspace brick
    project = _make_project(tmp_path, "consumer_app", {"consumer", "log", "phantom"})

    issues = check_project(project, graph)

    assert issues.missing == []
    assert issues.extra == []


def test_check_project_no_base_falls_back_to_all_declared(tmp_path: Path) -> None:
    """When no base bricks are declared, all declared bricks are used as seeds."""
    bricks = [
        Brick(name="kafka", type=BrickType.COMPONENT, path="components/example/kafka"),
        Brick(name="log", type=BrickType.COMPONENT, path="components/example/log"),
    ]
    graph = _make_graph(bricks, [("kafka", "log")])
    project = _make_project(tmp_path, "lib_project", {"kafka"})

    issues = check_project(project, graph)

    # kafka is the seed, log is reachable, but log is not declared
    assert issues.missing == ["log"]
    assert issues.extra == []
