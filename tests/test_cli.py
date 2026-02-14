from pathlib import Path

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


def test_graph_command_fails_when_no_workspace_found(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(main, ["graph", "--root", str(tmp_path)])

    assert result.exit_code != 0
    assert "workspace.toml" in result.output
