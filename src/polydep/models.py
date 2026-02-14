from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class BrickType(str, Enum):
    COMPONENT = "component"
    BASE = "base"


@dataclass(frozen=True)
class Brick:
    name: str
    type: BrickType
    path: str


@dataclass(frozen=True)
class Workspace:
    namespace: str
    root: Path
    bricks: tuple[Brick, ...] = field(default_factory=tuple)
