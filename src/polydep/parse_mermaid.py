import re

# Optional label after a node ID: A[Label], A(Label), A{Label}
_NODE_LABEL = r"(?:\[[^\]]*\]|\([^)]*\)|\{[^}]*\})?"

# Arrow styles: -->, ---,  ==>, -.->
_ARROW = r"(?:-->|---|-\.->|==>)"

# Optional link text: -->|some text|
_LINK_TEXT = r"(?:\|[^|]*\|)?"

_EDGE_PATTERN = re.compile(
    rf"^\s*(?P<source>\w+){_NODE_LABEL}"
    rf"\s+{_ARROW}{_LINK_TEXT}\s+"
    rf"(?P<target>\w+){_NODE_LABEL}\s*$"
)

_SKIP_PATTERN = re.compile(
    r"^\s*(?:%%|graph\s|flowchart\s|subgraph\s|end\s*$|style\s|classDef\s|class\s)"
)


def parse_mermaid(content: str) -> set[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    for line in content.splitlines():
        if _SKIP_PATTERN.match(line):
            continue
        match = _EDGE_PATTERN.match(line)
        if match:
            edges.add((match.group("source"), match.group("target")))
    return edges
