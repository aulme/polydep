import tomllib
from pathlib import Path

from polydep.models import Brick, BrickType, Workspace


def _read_namespace(root: Path) -> str:
    workspace_toml = root / "workspace.toml"
    pyproject_toml = root / "pyproject.toml"

    if workspace_toml.exists():
        config_path = workspace_toml
    elif pyproject_toml.exists():
        config_path = pyproject_toml
    else:
        raise FileNotFoundError(
            "workspace.toml not found. Run polydep from within a Python Polylith workspace, "
            "or use --root to specify the workspace directory."
        )

    with open(config_path, "rb") as file:
        config = tomllib.load(file)

    return config["tool"]["polylith"]["namespace"]


def _scan_bricks(root: Path, namespace: str, directory: str, brick_type: BrickType) -> tuple[Brick, ...]:
    parent = root / directory / namespace
    if not parent.is_dir():
        return ()
    return tuple(
        Brick(name=child.name, type=brick_type, path=str(child.relative_to(root)))
        for child in parent.iterdir()
        if child.is_dir()
    )


def parse_workspace(root: Path) -> Workspace:
    namespace = _read_namespace(root)
    bricks = (
        _scan_bricks(root, namespace, "components", BrickType.COMPONENT)
        + _scan_bricks(root, namespace, "bases", BrickType.BASE)
    )
    return Workspace(namespace=namespace, root=root, bricks=bricks)
