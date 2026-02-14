from pathlib import Path

from polydep.models import Import
from polydep.workspace import parse_workspace


def _get_brick_imports(workspace_root: Path, brick_name: str) -> dict[str, tuple[Import, ...]]:
    """Return {relative_file_path: imports} for a given brick."""
    workspace = parse_workspace(workspace_root)
    by_name = {brick.name: brick for brick in workspace.bricks}
    brick = by_name[brick_name]
    return {source_file.path: source_file.imports for source_file in brick.files}


def _create_single_brick_workspace(tmp_path: Path, filename: str, content: str) -> None:
    """Create a minimal workspace with one brick containing one file."""
    (tmp_path / "workspace.toml").write_text('[tool.polylith]\nnamespace = "ns"\n')
    brick_dir = tmp_path / "components" / "ns" / "foo"
    brick_dir.mkdir(parents=True)
    (brick_dir / "__init__.py").write_text("")
    (brick_dir / filename).write_text(content)


def test_extract_imports_from_simple_module(sample_project: Path) -> None:
    file_imports = _get_brick_imports(sample_project, "greeting")

    core_imports = file_imports["components/example/greeting/core.py"]
    assert core_imports == ()


def test_extract_imports_from_module_with_cross_brick_imports(sample_project: Path) -> None:
    file_imports = _get_brick_imports(sample_project, "greet_api")

    core_imports = file_imports["bases/example/greet_api/core.py"]
    modules = {imp.module for imp in core_imports}
    assert "example.greeting" in modules
    assert "example.log" in modules


def test_extract_imports_records_line_numbers(sample_project: Path) -> None:
    file_imports = _get_brick_imports(sample_project, "greet_api")

    core_imports = file_imports["bases/example/greet_api/core.py"]
    by_module = {imp.module: imp for imp in core_imports}

    assert by_module["example.greeting"].line == 3
    assert by_module["example.log"].line == 4


def test_extract_imports_records_statements(sample_project: Path) -> None:
    file_imports = _get_brick_imports(sample_project, "greet_api")

    core_imports = file_imports["bases/example/greet_api/core.py"]
    by_module = {imp.module: imp for imp in core_imports}

    assert by_module["example.greeting"].statement == "from example import greeting"
    assert by_module["example.log"].statement == "from example.log import get_logger"


def test_extract_imports_includes_stdlib_and_third_party(sample_project: Path) -> None:
    file_imports = _get_brick_imports(sample_project, "message")

    core_imports = file_imports["components/example/message/core.py"]
    modules = {imp.module for imp in core_imports}
    assert "json" in modules


def test_extract_imports_from_brick_with_many_dependencies(sample_project: Path) -> None:
    file_imports = _get_brick_imports(sample_project, "message")

    core_imports = file_imports["components/example/message/core.py"]
    modules = {imp.module for imp in core_imports}
    assert modules >= {
        "json",
        "example.kafka",
        "example.database",
        "example.database.message",
        "example.dictionaries",
        "example.schema",
    }


def test_extract_imports_skips_relative_imports(tmp_path: Path) -> None:
    _create_single_brick_workspace(
        tmp_path, "core.py", "from . import helper\nfrom .util import something\n"
    )

    workspace = parse_workspace(tmp_path)

    brick = workspace.bricks[0]
    core_file = next(f for f in brick.files if f.path.endswith("core.py"))
    assert core_file.imports == ()


def test_extract_imports_includes_type_checking_block(tmp_path: Path) -> None:
    _create_single_brick_workspace(
        tmp_path,
        "core.py",
        "from __future__ import annotations\n"
        "import os\n"
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    import sys\n"
        "    from collections import OrderedDict\n",
    )

    workspace = parse_workspace(tmp_path)

    brick = workspace.bricks[0]
    core_file = next(f for f in brick.files if f.path.endswith("core.py"))
    modules = {imp.module for imp in core_file.imports}
    assert modules >= {"__future__", "os", "typing", "sys", "collections"}


def test_extract_imports_handles_syntax_error(tmp_path: Path) -> None:
    _create_single_brick_workspace(tmp_path, "broken.py", "def f(\n")

    workspace = parse_workspace(tmp_path)

    brick = workspace.bricks[0]
    broken_file = next(f for f in brick.files if f.path.endswith("broken.py"))
    assert broken_file.imports == ()
