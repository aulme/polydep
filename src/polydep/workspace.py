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


def _enumerate_bricks(root: Path, namespace: str) -> tuple[Brick, ...]:
    bricks: list[Brick] = []

    for brick_type, directory in ((BrickType.COMPONENT, "components"), (BrickType.BASE, "bases")):
        parent = root / directory / namespace
        if not parent.is_dir():
            continue
        for child in sorted(parent.iterdir()):
            if child.is_dir():
                relative_path = child.relative_to(root)
                bricks.append(Brick(
                    name=child.name,
                    type=brick_type,
                    path=str(relative_path),
                ))

    return tuple(sorted(bricks, key=lambda brick: brick.name))


def parse_workspace(root: Path) -> Workspace:
    namespace = _read_namespace(root)
    bricks = _enumerate_bricks(root, namespace)
    return Workspace(namespace=namespace, root=root, bricks=bricks)
