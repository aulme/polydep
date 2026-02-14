from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class BrickType(str, Enum):
    COMPONENT = "component"
    BASE = "base"


@dataclass(frozen=True)
class Import:
    module: str
    line: int
    statement: str


@dataclass(frozen=True)
class SourceFile:
    path: str
    imports: tuple[Import, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Brick:
    name: str
    type: BrickType
    path: str
    files: tuple[SourceFile, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Workspace:
    namespace: str
    root: Path
    bricks: tuple[Brick, ...] = field(default_factory=tuple)
