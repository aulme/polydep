"""Greeting API entry point (stub)."""

from example import greeting
from example.log import get_logger

logger = get_logger("greet-API-logger")


def app() -> dict:
    logger.info("The greeting endpoint was called.")
    return {"message": greeting.hello_world()}
