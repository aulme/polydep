from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class BrickType(StrEnum):
    COMPONENT = "component"
    BASE = "base"


@dataclass
class Import:
    module: str
    line: int
    statement: str


@dataclass
class SourceFile:
    path: str
    imports: list[Import] = field(default_factory=list)


@dataclass
class Brick:
    name: str
    type: BrickType
    path: str
    files: list[SourceFile] = field(default_factory=list)


@dataclass
class Workspace:
    namespace: str
    root: Path
    bricks: list[Brick] = field(default_factory=list)


@dataclass
class ImportLocation:
    file: str
    line: int
    statement: str


@dataclass
class Edge:
    source: str
    target: str
    imports: list[ImportLocation] = field(default_factory=list)


@dataclass
class DependencyGraph:
    namespace: str
    bricks: list[Brick]
    edges: list[Edge] = field(default_factory=list)


@dataclass
class Project:
    name: str
    root: Path
    pyproject_path: Path
    declared_bricks: set[str]  # brick names only (not paths)


@dataclass
class ProjectIssues:
    project: Project
    missing: list[str]  # sorted brick names needed but not declared
    extra: list[str]  # sorted brick names declared but not needed by transitive closure
