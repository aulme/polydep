from dataclasses import dataclass


@dataclass
class Message:
    id: int | None = None
    content: str | None = None
