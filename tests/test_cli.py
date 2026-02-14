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

    assert result.exit_code != 0
    assert "nonexistent" in result.output
    assert "not found" in result.output
