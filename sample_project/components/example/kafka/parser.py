"""Kafka message parser (stub)."""

from typing import Any


def parse_message(msg: Any) -> tuple[str, str, str]:
    return ("topic", "key", "value")
