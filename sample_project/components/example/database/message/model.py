"""Message database model (stub)."""


class Message:
    __tablename__ = "messages"

    def __init__(self, id: int | None = None, content: str | None = None) -> None:
        self.id = id
        self.content = content
