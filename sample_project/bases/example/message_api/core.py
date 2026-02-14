"""Message API entry point (stub)."""

from example import log, message
from example.database import Session, engine
from example.schema import Message

logger = log.get_logger("message-API-logger")


def create(content: str) -> int:
    logger.info("Creating a message with content=%s", content)
    return message.create(content)


def read(message_id: int) -> dict:
    logger.info("Fetching message with id=%s", message_id)
    return message.read(message_id)


def update(message_id: int, content: str) -> None:
    logger.info("Updating message with id=%s", message_id)
    return message.update(message_id, content)


def delete(message_id: int) -> None:
    logger.info("Deleting message with id=%s", message_id)
    return message.delete(message_id)
