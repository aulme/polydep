# CLAUDE.md

## Project overview

polydep is a CLI tool that analyzes Python Polylith workspaces to produce dependency graphs, explain dependency chains, and enforce architectural boundaries between bricks.

## Terminology

| Term | Meaning |
|------|---------|
| **Workspace** | The monorepo root containing `workspace.toml` |
| **Brick** | A namespace package under `components/` or `bases/` |
| **Component** | A brick under `components/` — reusable internal code |
| **Base** | A brick under `bases/` — external-facing entry point |
| **Namespace** | The top-level Python package name (from `[tool.polylith].namespace`) |
| **Direct dependency** | Brick A imports brick B |
| **Transitive dependency** | Brick A depends on B through one or more intermediate bricks |

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

## Error handling

- Use `click.ClickException` for user-facing errors (prints message and exits with code 1)
- Errors must include enough context to be actionable, e.g.:
  - `"workspace.toml not found. Run polydep from within a Python Polylith workspace, or use --root to specify the workspace directory."`
  - `"brick 'foo' not found. Available bricks: greeting, database, schema, log"`
- Files with syntax errors return empty imports (don't crash)

## Planned features

### `why` command

Find all paths from source to target brick using BFS/DFS with cycle detection. For each path, show the import provenance (file + line number) for every edge. Exit 0 whether path is found or not.

### `check` command

Compare actual dependency graph against an expected Mermaid file. Report three categories of failure:
- **Unexpected edges** — boundary violations (actual edges not in expected graph)
- **Missing edges** — stale graph (expected edges not in actual graph)
- **Unknown bricks** — bricks in workspace but not mentioned in expected graph

For each unexpected edge, list the specific files and line numbers causing the violation.

Exit codes: 0 = match, 1 = mismatch, 2 = error.

### Mermaid parsing (for `check`)

Parse only the subset relevant to dependency graphs:
- Edge declarations: `A --> B`, `A --- B`, `A ==> B`, `A -.-> B` (all treated as edges)
- `graph <direction>` or `flowchart <direction>` header
- Node declarations with labels: `A[Label]`, `A(Label)`, `A{Label}` — extract the ID before brackets
- Link text: `A -->|text| B` — extract A and B, ignore text
- Subgraph blocks, comments (`%%`)
- Ignore: styling (`style`, `classDef`, `class`), click handlers

## Non-goals

- Modifying workspace files (read-only tool)
- Replacing existing `poly` CLI functionality
- Analyzing third-party library dependencies
- Supporting non-Python polylith implementations
