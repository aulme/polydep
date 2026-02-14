"""Kafka configuration (stub)."""

import os


def fetch_default_config() -> dict:
    return {"bootstrap.servers": "localhost:9092"}


def fetch_consumer_config() -> dict:
    return {"group.id": "python_example_group_1", "auto.offset.reset": "earliest"}


def is_enabled() -> bool:
    return os.environ.get("kafka", "") == "enabled"
