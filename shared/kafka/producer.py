"""
STAR
Situation: Streaming examples need a repeatable way to publish realistic events.
Task: Build a local Kafka producer using the shared event envelope.
Action: Generate deterministic order events and publish them with trace ids.
Result: Local Kafka tests can exercise consumers, Flink jobs, and Spark streaming jobs.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from confluent_kafka import Producer

from shared.python.event_envelope import EventEnvelope


def delivery_report(error, message) -> None:
    """Log delivery result for local troubleshooting."""
    if error is not None:
        print(f"delivery_failed topic={message.topic()} error={error}")
    else:
        print(f"delivered topic={message.topic()} partition={message.partition()} offset={message.offset()}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", default="localhost:9092")
    parser.add_argument("--topic", default="orders.raw")
    parser.add_argument("--count", type=int, default=25)
    args = parser.parse_args()

    producer = Producer({"bootstrap.servers": args.bootstrap})
    random.seed(42)

    for index in range(args.count):
        event = EventEnvelope.create(
            event_type="order_created",
            source_system="local_generator",
            payload={
                "order_id": f"ord_{index:05d}",
                "customer_id": f"cust_{random.randint(1, 10):04d}",
                "amount": round(random.uniform(10, 500), 2),
                "currency": "USD",
            },
        )
        producer.produce(args.topic, key=event.event_id, value=event.to_json(), callback=delivery_report)
        producer.poll(0)
        time.sleep(0.05)

    producer.flush()


if __name__ == "__main__":
    main()
