import shutil
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from polydep.cli import main


def test_graph_command(sample_project: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(main, ["graph", "--root", str(sample_project)])

    assert result.exit_code == 0
    assert result.output == (
        "graph LR\n"
        "  subgraph bases\n"
        "    consumer\n"
        "    greet_api\n"
        "    message_api\n"
        "  end\n"
        "  subgraph components\n"
        "    database\n"
        "    dictionaries\n"
        "    greeting\n"
        "    kafka\n"
        "    log\n"
        "    message\n"
        "    schema\n"
        "  end\n"
        "  consumer --> kafka\n"
        "  consumer --> log\n"
        "  greet_api --> greeting\n"
        "  greet_api --> log\n"
        "  kafka --> log\n"
        "  message --> database\n"
        "  message --> dictionaries\n"
        "  message --> kafka\n"
        "  message --> schema\n"
        "  message_api --> database\n"
        "  message_api --> log\n"
        "  message_api --> message\n"
        "  message_api --> schema\n"
    )


def test_graph_command_save(sample_project: Path, tmp_path: Path) -> None:
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["graph", "--save", "--root", str(sample_project)])

        assert result.exit_code == 0
        assert result.output == ""
        saved = Path("polydep.expected.mermaid").read_text()
        assert saved.startswith("graph LR\n")
        assert "consumer --> kafka\n" in saved


def test_graph_command_fails_when_no_workspace_found(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(main, ["graph", "--root", str(tmp_path)])

    assert result.exit_code != 0
    assert "workspace.toml" in result.output


def test_why_command_direct_dependency(sample_project: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(main, ["why", "greet_api", "greeting", "--root", str(sample_project)])

    assert result.exit_code == 0
    assert result.output == (
        "greet_api depends on greeting via 1 path:\n"
        "\n"
        "Path 1 (direct):\n"
        "  greet_api -> greeting\n"
        "    bases/example/greet_api/core.py:3  from example import greeting\n"
    )


def test_why_command_direct_and_transitive(sample_project: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(main, ["why", "consumer", "log", "--root", str(sample_project)])

    assert result.exit_code == 0
    assert result.output == (
        "consumer depends on log via 2 paths:\n"
        "\n"
        "Path 1 (direct):\n"
        "  consumer -> log\n"
        "    bases/example/consumer/core.py:3  from example import kafka, log\n"
        "\n"
        "Path 2 (transitive, length 2):\n"
        "  consumer -> kafka -> log\n"
        "    bases/example/consumer/core.py:3  from example import kafka, log\n"
        "    components/example/kafka/consumer.py:5  from example import log\n"
        "    components/example/kafka/producer.py:3  from example import log\n"
    )


def test_why_command_no_dependency(sample_project: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(main, ["why", "greet_api", "database", "--root", str(sample_project)])

    assert result.exit_code == 0
    assert result.output == "greet_api does not depend on database.\n"


def test_why_command_unknown_brick(sample_project: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(main, ["why", "nonexistent", "greeting", "--root", str(sample_project)])

    assert result.exit_code == 1
    assert result.output == (
        "Error: Brick 'nonexistent' not found."
        " Available bricks: consumer, database, dictionaries,"
        " greet_api, greeting, kafka, log, message, message_api, schema\n"
    )


def test_check_command_passes_on_match(sample_project: Path, tmp_path: Path) -> None:
    runner = CliRunner()
    graph_result = runner.invoke(main, ["graph", "--root", str(sample_project)])
    expected_file = tmp_path / "expected.mermaid"
    expected_file.write_text(graph_result.output)

    result = runner.invoke(
        main, ["check", "--expected", str(expected_file), "--root", str(sample_project)]
    )

    assert result.exit_code == 0
    assert result.output == "Check passed.\n"


def test_check_command_uses_default_path(sample_project: Path, tmp_path: Path) -> None:
    runner = CliRunner()
    graph_result = runner.invoke(main, ["graph", "--root", str(sample_project)])

    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("polydep.expected.mermaid").write_text(graph_result.output)

        result = runner.invoke(main, ["check", "--root", str(sample_project)])

    assert result.exit_code == 0
    assert result.output == "Check passed.\n"


def test_check_command_detects_unexpected_edges(sample_project: Path, tmp_path: Path) -> None:
    runner = CliRunner()
    graph_result = runner.invoke(main, ["graph", "--root", str(sample_project)])
    content = graph_result.output.replace("  consumer --> kafka\n", "")
    expected_file = tmp_path / "expected.mermaid"
    expected_file.write_text(content)

    result = runner.invoke(
        main, ["check", "--expected", str(expected_file), "--root", str(sample_project)]
    )

    assert result.exit_code == 1
    assert result.output == (
        "Check failed.\n"
        "\n"
        f"Unexpected dependencies (in project but not in {expected_file}):\n"
        "  consumer --> kafka\n"
        "    bases/example/consumer/core.py:3  from example import kafka, log\n"
    )


def test_check_command_detects_missing_edges(sample_project: Path, tmp_path: Path) -> None:
    runner = CliRunner()
    graph_result = runner.invoke(main, ["graph", "--root", str(sample_project)])
    content = graph_result.output + "  greeting --> database\n"
    expected_file = tmp_path / "expected.mermaid"
    expected_file.write_text(content)

    result = runner.invoke(
        main, ["check", "--expected", str(expected_file), "--root", str(sample_project)]
    )

    assert result.exit_code == 1
    assert result.output == (
        "Check failed.\n"
        "\n"
        f"Missing dependencies (in {expected_file} but not in project):\n"
        "  greeting --> database\n"
    )


def test_check_command_detects_both(sample_project: Path, tmp_path: Path) -> None:
    runner = CliRunner()
    graph_result = runner.invoke(main, ["graph", "--root", str(sample_project)])
    content = graph_result.output.replace("  consumer --> kafka\n", "")
    content += "  greeting --> database\n"
    expected_file = tmp_path / "expected.mermaid"
    expected_file.write_text(content)

    result = runner.invoke(
        main, ["check", "--expected", str(expected_file), "--root", str(sample_project)]
    )

    assert result.exit_code == 1
    assert result.output == (
        "Check failed.\n"
        "\n"
        f"Unexpected dependencies (in project but not in {expected_file}):\n"
        "  consumer --> kafka\n"
        "    bases/example/consumer/core.py:3  from example import kafka, log\n"
        "\n"
        f"Missing dependencies (in {expected_file} but not in project):\n"
        "  greeting --> database\n"
    )


def test_check_command_default_file_not_found(tmp_path: Path) -> None:
    (tmp_path / "workspace.toml").write_text(
        '[tool.polylith]\nnamespace = "example"\n', encoding="utf-8"
    )
    runner = CliRunner()

    result = runner.invoke(main, ["check", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "polydep.expected.mermaid" in result.output
    assert "not found" in result.output


# --- check --no-cycles tests ---


def _make_cyclic_workspace(root: Path) -> None:
    (root / "workspace.toml").write_text(
        '[tool.polylith]\nnamespace = "example"\n', encoding="utf-8"
    )
    alpha = root / "components" / "example" / "alpha"
    alpha.mkdir(parents=True)
    (alpha / "core.py").write_text("from example import beta\n", encoding="utf-8")
    beta = root / "components" / "example" / "beta"
    beta.mkdir(parents=True)
    (beta / "core.py").write_text("from example import alpha\n", encoding="utf-8")


def _make_transitive_cycle_workspace(root: Path) -> None:
    # a -> b -> c -> a: a multi-level cycle where no two bricks import each other directly.
    (root / "workspace.toml").write_text(
        '[tool.polylith]\nnamespace = "example"\n', encoding="utf-8"
    )
    for brick, imports in (("a", "b"), ("b", "c"), ("c", "a")):
        package = root / "components" / "example" / brick
        package.mkdir(parents=True)
        (package / "core.py").write_text(f"from example import {imports}\n", encoding="utf-8")


def test_check_no_cycles_detects_transitive_cycle(tmp_path: Path) -> None:
    _make_transitive_cycle_workspace(tmp_path)
    runner = CliRunner()
    # Every actual edge is declared, so the Mermaid check alone would pass.
    expected_file = tmp_path / "expected.mermaid"
    expected_file.write_text("graph LR\n  a --> b\n  b --> c\n  c --> a\n", encoding="utf-8")

    result = runner.invoke(
        main,
        ["check", "--no-cycles", "--expected", str(expected_file), "--root", str(tmp_path)],
    )

    assert result.exit_code == 1
    assert result.output == (
        "Check failed.\n\nCircular dependencies detected:\n  a -> b -> c -> a\n"
    )


def test_check_no_cycles_fails_even_when_cycle_is_in_mermaid(tmp_path: Path) -> None:
    _make_cyclic_workspace(tmp_path)
    runner = CliRunner()
    # The expected file *declares* the cyclic edges, so the Mermaid check alone would pass.
    expected_file = tmp_path / "expected.mermaid"
    expected_file.write_text("graph LR\n  alpha --> beta\n  beta --> alpha\n", encoding="utf-8")

    result = runner.invoke(
        main,
        ["check", "--no-cycles", "--expected", str(expected_file), "--root", str(tmp_path)],
    )

    assert result.exit_code == 1
    assert result.output == (
        "Check failed.\n\nCircular dependencies detected:\n  alpha -> beta -> alpha\n"
    )


def test_check_no_cycles_takes_priority_over_missing_expected_file(tmp_path: Path) -> None:
    _make_cyclic_workspace(tmp_path)
    runner = CliRunner()

    # No expected file exists — the cycle failure must take priority over the file-not-found error.
    result = runner.invoke(main, ["check", "--no-cycles", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert result.output == (
        "Check failed.\n\nCircular dependencies detected:\n  alpha -> beta -> alpha\n"
    )


def test_check_no_cycles_then_runs_mermaid_check_when_acyclic(
    sample_project: Path, tmp_path: Path
) -> None:
    runner = CliRunner()
    graph_result = runner.invoke(main, ["graph", "--root", str(sample_project)])
    expected_file = tmp_path / "expected.mermaid"
    expected_file.write_text(graph_result.output)

    result = runner.invoke(
        main,
        ["check", "--no-cycles", "--expected", str(expected_file), "--root", str(sample_project)],
    )

    assert result.exit_code == 0
    assert result.output == "Check passed.\n"


def test_check_no_cycles_acyclic_still_reports_mermaid_mismatch(
    sample_project: Path, tmp_path: Path
) -> None:
    runner = CliRunner()
    graph_result = runner.invoke(main, ["graph", "--root", str(sample_project)])
    content = graph_result.output.replace("  consumer --> kafka\n", "")
    expected_file = tmp_path / "expected.mermaid"
    expected_file.write_text(content)

    result = runner.invoke(
        main,
        ["check", "--no-cycles", "--expected", str(expected_file), "--root", str(sample_project)],
    )

    assert result.exit_code == 1
    assert result.output == (
        "Check failed.\n"
        "\n"
        f"Unexpected dependencies (in project but not in {expected_file}):\n"
        "  consumer --> kafka\n"
        "    bases/example/consumer/core.py:3  from example import kafka, log\n"
    )


def test_check_without_no_cycles_ignores_cycles(tmp_path: Path) -> None:
    _make_cyclic_workspace(tmp_path)
    runner = CliRunner()
    # Expected file matches the actual (cyclic) edges; without --no-cycles the check passes.
    expected_file = tmp_path / "expected.mermaid"
    expected_file.write_text("graph LR\n  alpha --> beta\n  beta --> alpha\n", encoding="utf-8")

    result = runner.invoke(
        main, ["check", "--expected", str(expected_file), "--root", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert result.output == "Check passed.\n"


def test_project_command_all_projects(sample_project: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(main, ["project", "--root", str(sample_project)])

    assert result.exit_code == 1
    assert result.output == (
        "consumer_app: 2 issue(s)\n"
        "  Missing (needed but not declared):\n"
        "    log\n"
        "  Extra (declared but not needed):\n"
        "    greeting\n"
        "messaging: OK\n"
    )


def test_project_command_single_project_with_issues(sample_project: Path) -> None:
    runner = CliRunner()
    consumer_app = sample_project / "projects" / "consumer_app"

    result = runner.invoke(main, ["project", str(consumer_app), "--root", str(sample_project)])

    assert result.exit_code == 1
    assert result.output == (
        "consumer_app: 2 issue(s)\n"
        "  Missing (needed but not declared):\n"
        "    log\n"
        "  Extra (declared but not needed):\n"
        "    greeting\n"
    )


def test_project_command_single_project_ok(sample_project: Path) -> None:
    runner = CliRunner()
    messaging = sample_project / "projects" / "messaging"

    result = runner.invoke(main, ["project", str(messaging), "--root", str(sample_project)])

    assert result.exit_code == 0
    assert result.output == "messaging: OK\n"


def test_project_command_fix(sample_project: Path, tmp_path: Path) -> None:
    # Copy sample_project to a temp location so we can modify it safely
    workspace_copy = tmp_path / "workspace"
    shutil.copytree(sample_project, workspace_copy)
    consumer_app = workspace_copy / "projects" / "consumer_app"
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["project", str(consumer_app), "--fix", "--root", str(workspace_copy)],
    )

    assert result.exit_code == 0
    assert result.output == "consumer_app: fixed\n"

    updated = (consumer_app / "pyproject.toml").read_text(encoding="utf-8")
    assert '"../../components/example/log" = "example/log"' in updated
    assert '"../../components/example/greeting"' not in updated


def test_project_command_fix_all_projects(sample_project: Path, tmp_path: Path) -> None:
    workspace_copy = tmp_path / "workspace"
    shutil.copytree(sample_project, workspace_copy)
    runner = CliRunner()

    result = runner.invoke(main, ["project", "--fix", "--root", str(workspace_copy)])

    assert result.exit_code == 0
    assert result.output == "consumer_app: fixed\nmessaging: OK (no changes)\n"


def test_project_command_no_projects_dir(tmp_path: Path) -> None:
    # Create a minimal workspace with no projects/ dir
    (tmp_path / "workspace.toml").write_text(
        '[tool.polylith]\nnamespace = "example"\n', encoding="utf-8"
    )
    runner = CliRunner()

    result = runner.invoke(main, ["project", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert result.output == "No projects found.\n"


# --- view command tests ---


def test_view_command_opens_mermaid_file(tmp_path: Path) -> None:
    runner = CliRunner()

    with patch("webbrowser.open") as mock_open, runner.isolated_filesystem(temp_dir=tmp_path) as td:
        mermaid_file = Path(td) / "test.mermaid"
        mermaid_file.write_text("graph LR\n  a --> b\n", encoding="utf-8")
        result = runner.invoke(main, ["view", str(mermaid_file)])

    assert result.exit_code == 0
    mock_open.assert_called_once()
    url = mock_open.call_args[0][0]
    assert url.startswith("file://")
    assert url.endswith(".html")


def test_view_command_uses_namespace_as_title(tmp_path: Path) -> None:
    (tmp_path / "workspace.toml").write_text(
        '[tool.polylith]\nnamespace = "example"\n', encoding="utf-8"
    )
    mermaid_file = tmp_path / "polydep.expected.mermaid"
    mermaid_file.write_text("graph LR\n  a --> b\n", encoding="utf-8")
    runner = CliRunner()

    with patch("webbrowser.open") as mock_open:
        result = runner.invoke(main, ["view", str(mermaid_file)])

    assert result.exit_code == 0
    html_path = Path(mock_open.call_args[0][0].removeprefix("file://"))
    html = html_path.read_text(encoding="utf-8")
    assert "<title>example</title>" in html
    assert "<h1>example</h1>" in html


def test_view_command_falls_back_to_stem_without_workspace(tmp_path: Path) -> None:
    mermaid_file = tmp_path / "polydep.expected.mermaid"
    mermaid_file.write_text("graph LR\n  a --> b\n", encoding="utf-8")
    runner = CliRunner()

    with patch("webbrowser.open") as mock_open, runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["view", str(mermaid_file)])

    assert result.exit_code == 0
    html_path = Path(mock_open.call_args[0][0].removeprefix("file://"))
    html = html_path.read_text(encoding="utf-8")
    assert "<title>polydep.expected</title>" in html
    assert "<h1>polydep.expected</h1>" in html


def test_view_command_default_file(tmp_path: Path) -> None:
    runner = CliRunner()

    with patch("webbrowser.open") as mock_open, runner.isolated_filesystem(temp_dir=tmp_path) as td:
        Path(td, "polydep.expected.mermaid").write_text("graph LR\n  a --> b\n", encoding="utf-8")
        result = runner.invoke(main, ["view"])

    assert result.exit_code == 0
    mock_open.assert_called_once()


def test_view_command_missing_file_errors(tmp_path: Path) -> None:
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["view"])

    assert result.exit_code == 1
    assert "not found" in result.output


# --- graph --view flag tests ---


def test_graph_view_flag(sample_project: Path) -> None:
    runner = CliRunner()

    with patch("webbrowser.open") as mock_open:
        result = runner.invoke(main, ["graph", "--root", str(sample_project), "--view"])

    assert result.exit_code == 0
    assert result.output == ""
    mock_open.assert_called_once()


def test_graph_view_and_save_together(sample_project: Path, tmp_path: Path) -> None:
    runner = CliRunner()

    with patch("webbrowser.open") as mock_open, runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(main, ["graph", "--root", str(sample_project), "--view", "--save"])
        saved = Path(td, "polydep.expected.mermaid").read_text()

    assert result.exit_code == 0
    assert result.output == ""
    mock_open.assert_called_once()
    assert saved.startswith("graph LR\n")


def _make_gitignore_workspace(root: Path) -> None:
    (root / "workspace.toml").write_text(
        '[tool.polylith]\nnamespace = "example"\n', encoding="utf-8"
    )
    real = root / "components" / "example" / "real"
    real.mkdir(parents=True)
    (real / "core.py").write_text("")
    ghost = root / "components" / "example" / "ghost"
    ghost.mkdir(parents=True)
    (ghost / "core.py").write_text("")
    (root / ".gitignore").write_text("ghost/\n")


def test_graph_respects_gitignore_by_default(tmp_path: Path) -> None:
    _make_gitignore_workspace(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["graph", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "ghost" not in result.output
    assert "real" in result.output


def test_graph_no_ignore_includes_gitignored_bricks(tmp_path: Path) -> None:
    _make_gitignore_workspace(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["graph", "--no-ignore", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "ghost" in result.output
    assert "real" in result.output


def test_why_respects_gitignore_by_default(tmp_path: Path) -> None:
    _make_gitignore_workspace(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["why", "real", "ghost", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "ghost" in result.output
    assert "not found" in result.output


def test_check_respects_gitignore_by_default(tmp_path: Path) -> None:
    _make_gitignore_workspace(tmp_path)
    runner = CliRunner()
    expected_file = tmp_path / "expected.mermaid"
    expected_file.write_text("graph LR\n")

    result = runner.invoke(
        main, ["check", "--expected", str(expected_file), "--root", str(tmp_path)]
    )

    assert result.exit_code == 0
