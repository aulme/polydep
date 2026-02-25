# CLAUDE.md

## Project overview

polydep is a CLI tool that analyzes Python Polylith workspaces to produce dependency graphs, explain dependency chains, enforce architectural boundaries between bricks, and verify project brick declarations.

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

## Setup

```bash
git clone https://github.com/aulme/polydep.git
cd polydep
uv sync
```

## Updating the viewer bundle

`src/polydep/static/viewer.bundle.js` is copied from the `fishtail` npm package and committed. To update it after a new fishtail release:

```bash
bun run update-viewer
```

This runs `bun install` (updating `fishtail` to the latest version) then copies `dist/viewer.bundle.js` from the npm package into `src/polydep/static/`. Commit the updated `viewer.bundle.js` and `bun.lockb` together.

## Commands

```bash
uv run pytest                          # Run tests
uv run ruff check .                    # Lint
uv run ruff format --check .           # Check formatting
uv run ruff format .                   # Auto-format
uv run ty check src/ tests/            # Type check
uv run polydep graph --root sample_project  # Smoke test
uv run polydep project --root sample_project  # Smoke test project command
uv run polydep graph --root sample_project --view  # Smoke test viewer
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
  cli.py                  # Click CLI entry point (graph, why, check, project, view commands)
  workspace.py            # Config parsing, brick enumeration, file scanning with imports
  import_parser.py        # AST-based import extraction (pure function)
  graph.py                # Dependency graph construction from Workspace
  generate_mermaid.py     # Mermaid diagram generation
  parse_mermaid.py        # Mermaid diagram parsing (regex-based edge extraction)
  paths.py                # Path finding between bricks (DFS)
  project_workspace.py    # Project discovery and pyproject.toml parsing
  project_checker.py      # Transitive closure check: missing/extra brick detection
  project_fixer.py        # Rewrites [tool.polylith.bricks] with direct/transitive annotations
  models.py               # All data types: BrickType, Import, ImportLocation, SourceFile, Brick, Workspace, Edge, DependencyGraph, Project, ProjectIssues
  view.py                 # Browser viewer: HTML generation, cycle/group detection, webbrowser.open
  static/
    viewer.bundle.js      # Copied from fishtail npm package (see "Updating the viewer bundle")
tests/
  conftest.py                  # Shared fixtures (sample_project)
  test_cli.py                  # CLI integration tests via CliRunner
  test_workspace.py            # Workspace parsing tests
  test_import_parser.py        # Import extraction tests
  test_graph.py                # Graph construction tests
  test_generate_mermaid.py     # Mermaid generation tests
  test_parse_mermaid.py        # Mermaid parsing tests
  test_paths.py                # Path finding tests
  test_project_workspace.py    # Project discovery and parsing tests
  test_project_checker.py      # Transitive closure / issue detection tests
  test_project_fixer.py        # Fixed section generation and apply_fix tests
sample_project/                # Polylith workspace fixture with 10 bricks under namespace "example"
  projects/
    consumer_app/              # Intentionally broken: missing log, extra greeting
    messaging/                 # Correctly declared
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

## Command behavior

### `graph`
Generates a Mermaid diagram with subgraph grouping by brick type (bases vs components). `--save` writes to `polydep.expected.mermaid`. `--view` opens the graph in the browser viewer (can be combined with `--save`). Without either flag, prints to stdout.

### `view`
Opens a `.mermaid` file in the browser viewer. Defaults to `polydep.expected.mermaid`. Parses subgraph membership and edges from the file, generates a self-contained HTML page with the inlined viewer bundle, writes it to a temp file, and calls `webbrowser.open`.

### `why`
Finds all paths from source to target brick using DFS with cycle detection. Each edge in a path carries import provenance (file, line, statement). Paths are sorted by length (direct first). Exit 0 whether path is found or not.

### `check`
Compares actual dependency graph against an expected Mermaid file (default: `polydep.expected.mermaid`). Reports unexpected edges (with file/line provenance) and missing edges. Exit codes: 0 = match, 1 = mismatch, 2 = error.

### `project`
Checks that each project's `[tool.polylith.bricks]` declares exactly the bricks reachable from its base bricks via transitive closure. Reports missing bricks (needed but not declared) and extra bricks (declared but not needed). `--fix` rewrites the section in place, splitting entries into `# direct` (bases + their 1-hop neighbours) and `# transitive` (rest of closure) blocks, with `# via <importers>` annotations on transitive entries. Exit codes: 0 = all OK or fix applied, 1 = issues found.

### Mermaid parsing
Regex-based parser that extracts edges from Mermaid syntax. Handles:
- Edge declarations: `A --> B`, `A --- B`, `A ==> B`, `A -.-> B`
- Node labels: `A[Label]`, `A(Label)`, `A{Label}`
- Link text: `A -->|text| B`
- Subgraphs, comments (`%%`), `graph`/`flowchart` headers
- Ignores: `style`, `classDef`, `class` lines

## CI/CD

GitHub Actions runs on every push and PR:

- **test** — `pytest`
- **lint** — `ruff check` + `ruff format --check`
- **typecheck** — `ty check`

On main, after all checks pass, a release is auto-created with an incremented `0.1.x` patch version and published to PyPI via trusted publisher (OIDC).

## Dependencies

| Dependency | Purpose |
|------------|---------|
| `click` | CLI framework (only runtime dependency) |
| `ast` (stdlib) | Import extraction |
| `tomllib` (stdlib) | Config parsing |

Dev tools: `uv`, `pytest`, `ruff`, `ty`

## Non-goals

- Modifying workspace files (read-only, except `polydep project --fix` which rewrites `pyproject.toml` bricks sections)
- Replacing existing `poly` CLI functionality
- Analyzing third-party library dependencies
- Supporting non-Python polylith implementations
