import tomllib
from pathlib import Path

from polydep.import_parser import extract_imports_from_source
from polydep.models import Brick, BrickType, SourceFile, Workspace


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


def _scan_files(root: Path, brick_path: Path, namespace: str) -> list[SourceFile]:
    return [
        SourceFile(
            path=str(py_file.relative_to(root)),
            imports=extract_imports_from_source(py_file.read_text(), namespace),
        )
        for py_file in brick_path.rglob("*.py")
    ]


def _scan_bricks(
    root: Path,
    namespace: str,
    directory: str,
    brick_type: BrickType,
) -> list[Brick]:
    parent = root / directory / namespace
    if not parent.is_dir():
        return []
    return [
        Brick(
            name=child.name,
            type=brick_type,
            path=str(child.relative_to(root)),
            files=_scan_files(root, child, namespace),
        )
        for child in parent.iterdir()
        if child.is_dir()
    ]


def parse_workspace(root: Path) -> Workspace:
    namespace = _read_namespace(root)
    bricks = _scan_bricks(root, namespace, "components", BrickType.COMPONENT) + _scan_bricks(
        root, namespace, "bases", BrickType.BASE
    )
    return Workspace(namespace=namespace, root=root, bricks=bricks)
