import ast

from polydep.models import Import


def _reconstruct_statement(node: ast.Import | ast.ImportFrom) -> str:
    if isinstance(node, ast.Import):
        names = ", ".join(alias.name for alias in node.names)
        return f"import {names}"
    module = node.module or ""
    names = ", ".join(alias.name for alias in node.names)
    return f"from {module} import {names}"


def _parse_plain_imports(node: ast.Import, statement: str) -> list[Import]:
    """`import X` or `import X, Y` — one Import per name."""
    return [
        Import(module=alias.name, line=node.lineno, statement=statement) for alias in node.names
    ]


def _parse_imports_from_namespace(
    node: ast.ImportFrom,
    namespace: str,
    statement: str,
) -> list[Import]:
    """`from <namespace> import X, Y` — qualify each name as <namespace>.X."""
    return [
        Import(module=f"{namespace}.{alias.name}", line=node.lineno, statement=statement)
        for alias in node.names
    ]


def _parse_import_from_qualified_module(node: ast.ImportFrom, statement: str) -> Import:
    """`from X.Y import Z` — module path already identifies the target."""
    return Import(module=node.module or "", line=node.lineno, statement=statement)


def extract_imports_from_source(source: str, namespace: str) -> tuple[Import, ...]:
    """Extract all absolute imports from Python source code.

    Walks the AST and collects imports into three categories:

    1. `import X` / `import X, Y` — each name becomes a separate Import
       with module set to the dotted name (e.g., "json", "os.path").

    2. `from <namespace> import X, Y` — in Polylith, importing directly from
       the namespace means each name is a brick (subpackage). We qualify them
       as "<namespace>.X" so downstream code can identify the target brick.

    3. `from X.Y import Z` — the module path already identifies the target,
       so we use it as-is (e.g., "example.log" from `from example.log import get_logger`).

    Relative imports (level > 0) are skipped since they're internal to a brick.
    Files with syntax errors return an empty tuple.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ()

    imports: list[Import] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.ImportFrom) and node.level > 0:
            continue

        statement = _reconstruct_statement(node)

        if isinstance(node, ast.Import):
            imports.extend(_parse_plain_imports(node, statement))
        elif node.module == namespace:
            imports.extend(_parse_imports_from_namespace(node, namespace, statement))
        else:
            imports.append(_parse_import_from_qualified_module(node, statement))

    return tuple(imports)
