"""
STAR
Situation: Event driven systems need consumers that validate contracts rather than blindly accepting messages.
Task: Build a simple Kafka consumer that parses the event envelope and reports bad records.
Action: Use the shared parser, commit offsets after successful validation, and print DLQ ready errors.
Result: The same pattern can be used before writing to Kafka DLQ, Kinesis DLQ, Event Hubs capture, or OCI Streaming retry topics.
"""

from __future__ import annotations

import argparse
from confluent_kafka import Consumer

from shared.python.event_envelope import parse_event


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", default="localhost:9092")
    parser.add_argument("--topic", default="orders.raw")
    parser.add_argument("--group", default="portfolio_validator")
    args = parser.parse_args()

    consumer = Consumer(
        {
            "bootstrap.servers": args.bootstrap,
            "group.id": args.group,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    consumer.subscribe([args.topic])

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"consumer_error={msg.error()}")
                continue
            try:
                event = parse_event(msg.value())
                print(f"valid_event event_id={event.event_id} event_type={event.event_type}")
                consumer.commit(msg)
            except Exception as exc:
                print(f"invalid_event partition={msg.partition()} offset={msg.offset()} error={exc}")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
