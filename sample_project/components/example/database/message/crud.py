"""CRUD operations for messages (stub)."""

from example.database.message.model import Message


def create(session: object, content: str) -> Message:
    return Message(id=1, content=content)


def read(session: object, message_id: int) -> Message | None:
    return Message(id=message_id, content="stub")


def update(session: object, existing: Message, content: str) -> None:
    existing.content = content


def delete(session: object, message_id: int) -> None:
    pass
