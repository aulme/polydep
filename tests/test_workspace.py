from pathlib import Path

import pytest

from polydep.models import Brick, BrickType, Workspace
from polydep.workspace import parse_workspace

SAMPLE_PROJECT = Path(__file__).resolve().parent.parent / "sample_project"


def test_parse_workspace_returns_correct_namespace_and_theme() -> None:
    workspace = parse_workspace(SAMPLE_PROJECT)

    assert workspace.namespace == "example"
    assert workspace.root == SAMPLE_PROJECT


def test_parse_workspace_finds_all_bricks() -> None:
    workspace = parse_workspace(SAMPLE_PROJECT)

    names = {brick.name for brick in workspace.bricks}
    assert names == {
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


def test_parse_workspace_classifies_brick_types() -> None:
    workspace = parse_workspace(SAMPLE_PROJECT)

    by_name = {brick.name: brick for brick in workspace.bricks}

    for name in ("database", "dictionaries", "greeting", "kafka", "log", "message", "schema"):
        assert by_name[name].type == BrickType.COMPONENT, f"{name} should be a component"

    for name in ("greet_api", "consumer", "message_api"):
        assert by_name[name].type == BrickType.BASE, f"{name} should be a base"


def test_parse_workspace_brick_paths() -> None:
    workspace = parse_workspace(SAMPLE_PROJECT)

    by_name = {brick.name: brick for brick in workspace.bricks}

    assert by_name["greeting"].path == "components/example/greeting"
    assert by_name["kafka"].path == "components/example/kafka"
    assert by_name["database"].path == "components/example/database"
    assert by_name["greet_api"].path == "bases/example/greet_api"
    assert by_name["consumer"].path == "bases/example/consumer"
    assert by_name["message_api"].path == "bases/example/message_api"


def test_parse_workspace_bricks_are_sorted_by_name() -> None:
    workspace = parse_workspace(SAMPLE_PROJECT)

    names = [brick.name for brick in workspace.bricks]
    assert names == sorted(names)


def test_parse_workspace_with_missing_config_raises(tmp_path: Path) -> None:
    (tmp_path / "components").mkdir()
    (tmp_path / "bases").mkdir()

    with pytest.raises(FileNotFoundError):
        parse_workspace(tmp_path)
