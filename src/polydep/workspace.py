import tomllib
from pathlib import Path

from pathspec import PathSpec

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


def _load_gitignore_specs(root: Path) -> list[tuple[Path, PathSpec]]:
    specs = []
    for gitignore_file in root.rglob(".gitignore"):
        lines = gitignore_file.read_text(encoding="utf-8").splitlines()
        spec = PathSpec.from_lines("gitignore", lines)
        specs.append((gitignore_file.parent, spec))
    return specs


def _is_path_ignored(path: Path, specs: list[tuple[Path, PathSpec]]) -> bool:
    for gitignore_dir, spec in specs:
        try:
            rel = path.relative_to(gitignore_dir).as_posix()
        except ValueError:
            continue
        if spec.match_file(rel):
            return True
    return False


def _collect_python_files(
    directory: Path,
    specs: list[tuple[Path, PathSpec]],
) -> list[Path]:
    result = []
    for child in directory.iterdir():
        if _is_path_ignored(child, specs):
            continue
        if child.is_dir():
            result.extend(_collect_python_files(child, specs))
        elif child.suffix == ".py":
            result.append(child)
    return result


def _scan_files(
    root: Path,
    brick_path: Path,
    namespace: str,
    specs: list[tuple[Path, PathSpec]],
) -> list[SourceFile]:
    return [
        SourceFile(
            path=py_file.relative_to(root).as_posix(),
            imports=extract_imports_from_source(py_file.read_text(encoding="utf-8"), namespace),
        )
        for py_file in _collect_python_files(brick_path, specs)
    ]


def _scan_bricks(
    root: Path,
    namespace: str,
    directory: str,
    brick_type: BrickType,
    specs: list[tuple[Path, PathSpec]],
) -> list[Brick]:
    parent = root / directory / namespace
    if not parent.is_dir():
        return []
    bricks = []
    for child in parent.iterdir():
        if not child.is_dir():
            continue
        if _is_path_ignored(child, specs):
            continue
        files = _scan_files(root, child, namespace, specs)
        if not files:
            continue
        bricks.append(
            Brick(
                name=child.name,
                type=brick_type,
                path=child.relative_to(root).as_posix(),
                files=files,
            )
        )
    return bricks


def parse_workspace(root: Path, ignore_gitignored: bool = True) -> Workspace:
    namespace = _read_namespace(root)
    specs = _load_gitignore_specs(root) if ignore_gitignored else []
    bricks = _scan_bricks(root, namespace, "components", BrickType.COMPONENT, specs) + _scan_bricks(
        root, namespace, "bases", BrickType.BASE, specs
    )
    return Workspace(namespace=namespace, root=root, bricks=bricks)
