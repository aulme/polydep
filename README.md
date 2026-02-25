# polydep

Dependency graph and boundary enforcement for Python Polylith workspaces.

`polydep` analyzes inter-brick imports in a [Python Polylith](https://github.com/DavidVujic/python-polylith) monorepo and outputs a Mermaid dependency graph. It complements the `poly` CLI by adding graph visualization, dependency chain explanation, and CI-friendly boundary checks.

Mostly read-only — `polydep project --fix` can rewrite `[tool.polylith.bricks]` sections.

## Install

```bash
pip install polydep
# or
uv tool install polydep
```

Requires Python 3.11+.

## Quick start

```bash
# Open the dependency graph in an interactive browser viewer
polydep graph --view

# Generate a dependency graph as Mermaid
polydep graph

# Specify a workspace root
polydep graph --root /path/to/workspace

# Save to polydep.expected.mermaid
polydep graph --save
```

Example output:

```mermaid
graph LR
  subgraph bases
    consumer
    greet_api
    message_api
  end
  subgraph components
    database
    dictionaries
    greeting
    kafka
    log
    message
    schema
  end
  consumer --> kafka
  consumer --> log
  greet_api --> greeting
  greet_api --> log
  kafka --> log
  message --> database
  message --> dictionaries
  message --> kafka
  message --> schema
  message_api --> database
  message_api --> log
  message_api --> message
  message_api --> schema
```

## Commands

### `polydep graph`

Print the dependency graph as a Mermaid diagram to stdout.

```bash
polydep graph [--root <path>] [--save] [--view]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--root <path>` | `.` | Workspace root directory |
| `--save` | | Write to `polydep.expected.mermaid` instead of printing |
| `--view` | | Open the graph in an interactive browser viewer |

`--view` and `--save` can be combined: saves the Mermaid file and opens the viewer.

### `polydep view`

Open a saved Mermaid diagram in the interactive browser viewer.

```bash
polydep view [<file>]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `<file>` | `polydep.expected.mermaid` | Path to a `.mermaid` file |

The viewer renders an interactive graph with transitive node highlighting, search, cycle detection, and connected-component grouping. The tab title and sidebar logo show the workspace namespace (e.g. `myapp`) — inferred from the `workspace.toml` in the same directory as the file.

### `polydep why`

Explain why brick A depends on brick B — shows all dependency paths with exact file and line provenance.

```bash
polydep why <source_brick> <target_brick> [--root <path>]
```

Example output:

```
consumer depends on log via 2 paths:

Path 1 (direct):
  consumer -> log
    bases/example/consumer/core.py:3  from example import kafka, log

Path 2 (transitive, length 2):
  consumer -> kafka -> log
    bases/example/consumer/core.py:3  from example import kafka, log
    components/example/kafka/consumer.py:5  from example import log
    components/example/kafka/producer.py:3  from example import log
```

### `polydep project`

Check that each project's `pyproject.toml` declares exactly the bricks it needs — no missing, no stale extras. Computes the full transitive closure from the project's base bricks.

```bash
polydep project [<project_path>] [--fix] [--root <path>]
```

| Flag | Default | Description |
|------|---------|-------------|
| `<project_path>` | | Single project directory to check (omit to scan all `projects/*/`) |
| `--fix` | | Rewrite `[tool.polylith.bricks]` with the correct set |
| `--root <path>` | `.` | Workspace root directory |

Example output (issues found):

```
consumer_app: 2 issue(s)
  Missing (needed but not declared):
    log
  Extra (declared but not needed):
    greeting
messaging: OK
```

The `--fix` flag rewrites the bricks section in place, grouping entries into `# direct` (base bricks and their immediate imports) and `# transitive` (everything else), with `# via` annotations showing which bricks pull each transitive one in:

```toml
[tool.polylith.bricks]
# direct
"../../bases/example/message_api" = "example/message_api"
"../../components/example/database" = "example/database"
"../../components/example/log" = "example/log"
"../../components/example/message" = "example/message"
"../../components/example/schema" = "example/schema"

# transitive
"../../components/example/dictionaries" = "example/dictionaries"  # via message
"../../components/example/kafka" = "example/kafka"  # via message
```

| Exit code | Meaning |
|-----------|---------|
| 0 | All projects OK (or `--fix` applied) |
| 1 | Issues found (without `--fix`) |

### `polydep check`

Compare actual dependencies against an expected graph file. Designed for CI — exits non-zero on mismatch.

```bash
polydep check [--expected <path>] [--root <path>]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--expected <path>` | `polydep.expected.mermaid` | Path to expected graph file |
| `--root <path>` | `.` | Workspace root directory |

The expected graph file is a Mermaid file, typically generated by `polydep graph --save`. Strict comparison — unexpected edges (boundary violations) and missing edges (stale graph) cause failure. Unexpected edges include file and line provenance.

When the graph matches:

```
Check passed.
```

When there are violations:

```
Check failed.

Unexpected dependencies:
  consumer --> database
    bases/example/consumer/core.py:3  from example import database, kafka, log

Missing dependencies:
  greet_api --> log
```

| Exit code | Meaning |
|-----------|---------|
| 0 | Actual graph matches expected graph |
| 1 | Mismatch detected |
| 2 | Error (file not found, parse error, etc.) |

## CI integration

### Bootstrap an expected graph

```bash
polydep graph --save
git add polydep.expected.mermaid && git commit -m "Add expected dependency graph"
```

### GitHub Actions

```yaml
- uses: astral-sh/setup-uv@v5
- run: uv tool install polydep
- run: polydep check
```

### Pre-commit hook

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: polydep-check
      name: polydep boundary check
      entry: uv run polydep check
      language: system
      pass_filenames: false
```

## How it works

1. **Workspace discovery** — finds `workspace.toml` (or `pyproject.toml` with `[tool.polylith]`) and reads the namespace
2. **Brick enumeration** — scans `components/<namespace>/*/` and `bases/<namespace>/*/`
3. **Import extraction** — parses every `.py` file with Python's `ast` module, collecting all absolute imports (relative imports are skipped as they're internal to a brick)
4. **Graph construction** — filters imports to those targeting known bricks (matching `<namespace>.<brick_name>`), excludes self-imports, and builds a deduplicated edge set
5. **Output** — renders the graph as a Mermaid diagram with subgraph grouping by brick type

## Comparison with `poly` CLI

| Feature | `poly` CLI | `polydep` |
|---------|-----------|-----------|
| Dependency table | `poly deps` | -- |
| Dependency graph (Mermaid) | -- | `polydep graph` |
| Interactive graph viewer | -- | `polydep graph --view`, `polydep view` |
| Dependency explanation | -- | `polydep why` |
| Boundary enforcement | -- | `polydep check` |
| Missing/extra deps in project | `poly check` | `polydep project` |
| Library analysis | `poly libs` | -- |

`polydep` complements rather than replaces `poly`. It focuses on the inter-brick dependency graph.