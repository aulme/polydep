"""Kafka producer (stub)."""

from example import log
from example.kafka.core import fetch_default_config, is_enabled
from example.kafka.parser import parse_message

logger = log.get_logger("Kafka-Producer-logger")


def produce(topic: str, key: str, value: str) -> None:
    if not is_enabled():
        return

    _ = fetch_default_config()
    _ = parse_message(None)
    logger.info("Produced: topic=%s key=%s value=%s", topic, key, value)
