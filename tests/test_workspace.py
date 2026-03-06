from pathlib import Path

import pytest

from polydep.models import BrickType
from polydep.workspace import parse_workspace


def test_parse_workspace_returns_correct_namespace_and_theme(sample_project: Path) -> None:
    workspace = parse_workspace(sample_project)

    assert workspace.namespace == "example"
    assert workspace.root == sample_project


def test_parse_workspace_finds_all_bricks(sample_project: Path) -> None:
    workspace = parse_workspace(sample_project)

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


def test_parse_workspace_classifies_brick_types(sample_project: Path) -> None:
    workspace = parse_workspace(sample_project)

    by_name = {brick.name: brick for brick in workspace.bricks}

    for name in ("database", "dictionaries", "greeting", "kafka", "log", "message", "schema"):
        assert by_name[name].type == BrickType.COMPONENT, f"{name} should be a component"

    for name in ("greet_api", "consumer", "message_api"):
        assert by_name[name].type == BrickType.BASE, f"{name} should be a base"


def test_parse_workspace_brick_paths(sample_project: Path) -> None:
    workspace = parse_workspace(sample_project)

    by_name = {brick.name: brick for brick in workspace.bricks}

    assert by_name["greeting"].path == "components/example/greeting"
    assert by_name["kafka"].path == "components/example/kafka"
    assert by_name["database"].path == "components/example/database"
    assert by_name["greet_api"].path == "bases/example/greet_api"
    assert by_name["consumer"].path == "bases/example/consumer"
    assert by_name["message_api"].path == "bases/example/message_api"


def test_parse_workspace_populates_files_for_simple_brick(sample_project: Path) -> None:
    workspace = parse_workspace(sample_project)

    by_name = {brick.name: brick for brick in workspace.bricks}
    greeting = by_name["greeting"]

    file_paths = {source_file.path for source_file in greeting.files}
    assert file_paths == {
        "components/example/greeting/__init__.py",
        "components/example/greeting/core.py",
    }


def test_parse_workspace_populates_files_recursively(sample_project: Path) -> None:
    workspace = parse_workspace(sample_project)

    by_name = {brick.name: brick for brick in workspace.bricks}
    database = by_name["database"]

    file_paths = {source_file.path for source_file in database.files}
    assert file_paths == {
        "components/example/database/__init__.py",
        "components/example/database/core.py",
        "components/example/database/message/__init__.py",
        "components/example/database/message/crud.py",
        "components/example/database/message/model.py",
    }


def test_parse_workspace_with_missing_config_raises(tmp_path: Path) -> None:
    (tmp_path / "components").mkdir()
    (tmp_path / "bases").mkdir()

    with pytest.raises(FileNotFoundError):
        parse_workspace(tmp_path)


def _make_workspace(root: Path) -> None:
    (root / "workspace.toml").write_text(
        '[tool.polylith]\nnamespace = "example"\n', encoding="utf-8"
    )


def test_gitignored_file_is_excluded(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    brick = tmp_path / "components" / "example" / "mycomp"
    brick.mkdir(parents=True)
    (brick / "core.py").write_text("x = 1")
    (brick / "generated.py").write_text("x = 2")
    (tmp_path / ".gitignore").write_text("generated.py\n")

    workspace = parse_workspace(tmp_path)

    mycomp = next(b for b in workspace.bricks if b.name == "mycomp")
    assert {sf.path for sf in mycomp.files} == {"components/example/mycomp/core.py"}


def test_gitignored_subdirectory_is_excluded(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    brick = tmp_path / "components" / "example" / "mycomp"
    brick.mkdir(parents=True)
    (brick / "core.py").write_text("x = 1")
    generated = brick / "generated"
    generated.mkdir()
    (generated / "code.py").write_text("x = 2")
    (tmp_path / ".gitignore").write_text("generated/\n")

    workspace = parse_workspace(tmp_path)

    mycomp = next(b for b in workspace.bricks if b.name == "mycomp")
    assert {sf.path for sf in mycomp.files} == {"components/example/mycomp/core.py"}


def test_nested_gitignore_is_respected(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    brick = tmp_path / "components" / "example" / "mycomp"
    brick.mkdir(parents=True)
    (brick / "core.py").write_text("x = 1")
    (brick / "secret.py").write_text("x = 2")
    (brick / ".gitignore").write_text("secret.py\n")

    workspace = parse_workspace(tmp_path)

    mycomp = next(b for b in workspace.bricks if b.name == "mycomp")
    assert {sf.path for sf in mycomp.files} == {"components/example/mycomp/core.py"}


def test_brick_entirely_gitignored_is_excluded(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    real = tmp_path / "components" / "example" / "real"
    real.mkdir(parents=True)
    (real / "core.py").write_text("x = 1")
    ghost = tmp_path / "components" / "example" / "ghost"
    ghost.mkdir(parents=True)
    (ghost / "code.py").write_text("x = 2")
    (tmp_path / ".gitignore").write_text("ghost/\n")

    workspace = parse_workspace(tmp_path)

    assert {b.name for b in workspace.bricks} == {"real"}


def test_brick_with_all_files_gitignored_is_excluded(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    real = tmp_path / "components" / "example" / "real"
    real.mkdir(parents=True)
    (real / "core.py").write_text("x = 1")
    hollow = tmp_path / "components" / "example" / "hollow"
    hollow.mkdir(parents=True)
    (hollow / "generated.py").write_text("x = 2")
    (tmp_path / ".gitignore").write_text("generated.py\n")

    workspace = parse_workspace(tmp_path)

    assert {b.name for b in workspace.bricks} == {"real"}


def test_no_ignore_includes_gitignored_files(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    brick = tmp_path / "components" / "example" / "mycomp"
    brick.mkdir(parents=True)
    (brick / "core.py").write_text("x = 1")
    (brick / "generated.py").write_text("x = 2")
    (tmp_path / ".gitignore").write_text("generated.py\n")

    workspace = parse_workspace(tmp_path, ignore_gitignored=False)

    mycomp = next(b for b in workspace.bricks if b.name == "mycomp")
    assert {sf.path for sf in mycomp.files} == {
        "components/example/mycomp/core.py",
        "components/example/mycomp/generated.py",
    }


def test_no_ignore_includes_gitignored_brick(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    real = tmp_path / "components" / "example" / "real"
    real.mkdir(parents=True)
    (real / "core.py").write_text("x = 1")
    ghost = tmp_path / "components" / "example" / "ghost"
    ghost.mkdir(parents=True)
    (ghost / "code.py").write_text("x = 2")
    (tmp_path / ".gitignore").write_text("ghost/\n")

    workspace = parse_workspace(tmp_path, ignore_gitignored=False)

    assert {b.name for b in workspace.bricks} == {"real", "ghost"}
