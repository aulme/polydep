from pathlib import Path

import pytest

from polydep.models import Workspace
from polydep.project_workspace import find_projects, parse_project


@pytest.fixture()
def minimal_workspace(tmp_path: Path) -> Workspace:
    return Workspace(namespace="example", root=tmp_path, bricks=[])


def test_parse_project_extracts_brick_names(tmp_path: Path, minimal_workspace: Workspace) -> None:
    project_dir = tmp_path / "my_app"
    project_dir.mkdir()
    (project_dir / "pyproject.toml").write_text(
        "[tool.polylith.bricks]\n"
        '"../../bases/example/consumer" = "example/consumer"\n'
        '"../../components/example/kafka" = "example/kafka"\n',
        encoding="utf-8",
    )

    result = parse_project(project_dir, minimal_workspace)

    assert result.name == "my_app"
    assert result.root == project_dir
    assert result.pyproject_path == project_dir / "pyproject.toml"
    assert result.declared_bricks == {"consumer", "kafka"}


def test_parse_project_empty_bricks_section(tmp_path: Path, minimal_workspace: Workspace) -> None:
    project_dir = tmp_path / "empty_app"
    project_dir.mkdir()
    (project_dir / "pyproject.toml").write_text(
        "[tool.polylith.bricks]\n",
        encoding="utf-8",
    )

    result = parse_project(project_dir, minimal_workspace)

    assert result.declared_bricks == set()


def test_parse_project_no_bricks_section(tmp_path: Path, minimal_workspace: Workspace) -> None:
    project_dir = tmp_path / "no_bricks_app"
    project_dir.mkdir()
    (project_dir / "pyproject.toml").write_text(
        '[project]\nname = "no_bricks_app"\n',
        encoding="utf-8",
    )

    result = parse_project(project_dir, minimal_workspace)

    assert result.declared_bricks == set()


def test_find_projects_returns_all_projects(tmp_path: Path, minimal_workspace: Workspace) -> None:
    projects_dir = tmp_path / "projects"
    for name in ("app_a", "app_b"):
        project_dir = projects_dir / name
        project_dir.mkdir(parents=True)
        (project_dir / "pyproject.toml").write_text(
            "[tool.polylith.bricks]\n",
            encoding="utf-8",
        )

    result = find_projects(tmp_path, minimal_workspace)

    assert [p.name for p in result] == ["app_a", "app_b"]


def test_find_projects_skips_dirs_without_pyproject(
    tmp_path: Path, minimal_workspace: Workspace
) -> None:
    projects_dir = tmp_path / "projects"
    (projects_dir / "app_a").mkdir(parents=True)
    (projects_dir / "app_a" / "pyproject.toml").write_text(
        "[tool.polylith.bricks]\n", encoding="utf-8"
    )
    (projects_dir / "not_a_project").mkdir()

    result = find_projects(tmp_path, minimal_workspace)

    assert [p.name for p in result] == ["app_a"]


def test_find_projects_returns_empty_when_no_projects_dir(
    tmp_path: Path, minimal_workspace: Workspace
) -> None:
    result = find_projects(tmp_path, minimal_workspace)

    assert result == []


def test_find_projects_uses_sample_project(sample_project: Path) -> None:
    from polydep.workspace import parse_workspace

    workspace = parse_workspace(sample_project)
    result = find_projects(sample_project, workspace)

    assert [p.name for p in result] == ["consumer_app", "messaging"]
    consumer_app = next(p for p in result if p.name == "consumer_app")
    assert consumer_app.declared_bricks == {"consumer", "kafka", "greeting"}
    messaging = next(p for p in result if p.name == "messaging")
    assert messaging.declared_bricks == {
        "message_api",
        "database",
        "dictionaries",
        "kafka",
        "log",
        "message",
        "schema",
    }
