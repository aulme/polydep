# CLAUDE.md

## Project overview

polydep is a CLI tool that analyzes Python Polylith workspaces to produce dependency graphs, explain dependency chains, and enforce architectural boundaries between bricks. See SPEC.md for the full design specification.

## Commands

```bash
uv run pytest                          # Run tests
uv run ruff check .                    # Lint
uv run ruff format --check .           # Check formatting
uv run ruff format .                   # Auto-format
uv run ty check src/ tests/            # Type check
uv run polydep graph --root sample_project  # Smoke test
```

All code must pass pytest, ruff check, ruff format --check, and ty check before committing.

## Code conventions

- **Functional style** with frozen dataclasses and tuples (not lists) for all data structures
- **Type annotations** on all function parameters and return types. Python 3.11+ syntax (`str | None`, `list[X]`, `tuple[X, ...]`)
- **No unnecessary abbreviations** — use `workspace` not `ws`, `brick` not `b`, `source_file` not `f`
- **Small focused modules** — each file has a single responsibility
- **Pure functions where possible** — `import_parser.py` takes a source string (no filesystem), `graph.py` takes a Workspace (no I/O)
- `sample_project/` is a test fixture, not production code — excluded from ruff and ty checks

## Test workflow

- **Always write tests before implementation** and present them for review
- **Unit tests** construct data objects directly in memory (no filesystem)
- **Integration tests** use the `sample_project` pytest fixture from `conftest.py`
- Prefer exact assertions over partial checks
- Keep test helpers minimal — filesystem setup in helpers, assertions inline in tests

## Project structure

```
src/polydep/
  cli.py             # Click CLI entry point
  workspace.py       # Config parsing, brick enumeration, file scanning with imports
  import_parser.py   # AST-based import extraction (pure function)
  graph.py           # Dependency graph construction from Workspace
  mermaid.py         # Mermaid diagram generation
  models.py          # All data types: BrickType, Import, SourceFile, Brick, Workspace, Edge, DependencyGraph
tests/
  conftest.py        # Shared fixtures (sample_project)
  test_cli.py        # CLI integration tests via CliRunner
  test_workspace.py  # Workspace parsing tests
  test_import_parser.py  # Import extraction tests
  test_graph.py      # Graph construction tests
  test_mermaid.py    # Mermaid generation tests
sample_project/      # Polylith workspace fixture with 10 bricks under namespace "example"
```

## Key design decisions

- TYPE_CHECKING imports are treated as real dependencies (not filtered out)
- Relative imports are skipped (internal to a brick)
- `parse_workspace` returns a fully populated Workspace with files and imports in one call
- The only runtime dependency is `click`
