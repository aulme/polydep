"""Kafka consumer (stub)."""

from typing import Callable

from example import log
from example.kafka.core import fetch_consumer_config, fetch_default_config
from example.kafka.parser import parse_message

logger = log.get_logger("Kafka-Consumer-logger")


def consume(topic: str, callback: Callable) -> None:
    logger.info("Consuming from topic=%s (stub)", topic)
    config = fetch_default_config() | fetch_consumer_config()
    _ = parse_message(None)
    callback(topic, "key", "value")
