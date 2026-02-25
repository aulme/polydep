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

_SUBGRAPH_PATTERN = re.compile(r"^\s*subgraph\s+(\S+)")
_END_PATTERN = re.compile(r"^\s*end\s*$")
_NODE_PATTERN = re.compile(r"^\s*(\w+)\s*$")


def parse_mermaid(content: str) -> set[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    for line in content.splitlines():
        if _SKIP_PATTERN.match(line):
            continue
        match = _EDGE_PATTERN.match(line)
        if match:
            edges.add((match.group("source"), match.group("target")))
    return edges


def parse_mermaid_with_subgraphs(
    text: str,
) -> tuple[dict[str, str], set[tuple[str, str]]]:
    """Parse a Mermaid graph and return (node_to_subgraph_name, edges).

    node_to_subgraph_name maps each node ID that appears in a subgraph block
    to that subgraph's name. Nodes that only appear in edges (not in any
    subgraph block) are not included.
    """
    node_subgraph: dict[str, str] = {}
    edges: set[tuple[str, str]] = set()
    current_subgraph: str | None = None

    for line in text.splitlines():
        sg_match = _SUBGRAPH_PATTERN.match(line)
        if sg_match:
            current_subgraph = sg_match.group(1)
            continue
        if _END_PATTERN.match(line):
            current_subgraph = None
            continue
        edge_match = _EDGE_PATTERN.match(line)
        if edge_match:
            edges.add((edge_match.group("source"), edge_match.group("target")))
            continue
        if current_subgraph is not None:
            node_match = _NODE_PATTERN.match(line)
            if node_match:
                node_subgraph[node_match.group(1)] = current_subgraph

    return node_subgraph, edges
