import tomllib
from pathlib import Path

from polydep.models import Project, Workspace


def parse_project(project_dir: Path, workspace: Workspace) -> Project:
    pyproject_path = project_dir / "pyproject.toml"
    with open(pyproject_path, "rb") as file:
        config = tomllib.load(file)

    bricks_section: dict[str, str] = config.get("tool", {}).get("polylith", {}).get("bricks", {})
    declared_bricks = {Path(key).name for key in bricks_section}

    return Project(
        name=project_dir.name,
        root=project_dir,
        pyproject_path=pyproject_path,
        declared_bricks=declared_bricks,
    )


def find_projects(workspace_root: Path, workspace: Workspace) -> list[Project]:
    projects_dir = workspace_root / "projects"
    if not projects_dir.is_dir():
        return []
    return [
        parse_project(project_dir, workspace)
        for project_dir in sorted(projects_dir.iterdir())
        if project_dir.is_dir() and (project_dir / "pyproject.toml").exists()
    ]
