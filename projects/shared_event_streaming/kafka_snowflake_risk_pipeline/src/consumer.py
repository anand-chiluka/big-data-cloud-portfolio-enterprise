"""
STAR
Situation: The pipeline logic is tested in isolation, but it still needs a long-running Kafka worker.
Task: Wrap RiskPipeline in a consumer that batches, commits only after durable writes, and dead-letters bad events.
Action: Poll in small batches, run the pipeline, publish dead letters to a DLQ topic, then commit offsets for the batch.
Result: At-least-once delivery with effectively-once table state, since replays hit the idempotent MERGE.

Note: confluent_kafka and snowflake are imported inside main() so this module imports cleanly in tests and in
the container health check without a broker.
"""

from __future__ import annotations

import json
import os

from src.pipeline import RiskPipeline


def main() -> None:
    from confluent_kafka import Consumer, Producer  # noqa: PLC0415

    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic = os.environ.get("RISK_TOPIC", "payments.raw")
    dlq_topic = os.environ.get("RISK_DLQ_TOPIC", "payments.dlq")
    batch_size = int(os.environ.get("BATCH_SIZE", "100"))

    sink = _build_sink()
    pipeline = RiskPipeline(sink)
    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": "risk_pipeline",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    dlq = Producer({"bootstrap.servers": bootstrap})
    consumer.subscribe([topic])
    try:
        while True:
            messages = consumer.consume(num_messages=batch_size, timeout=1.0)
            valid = [m for m in messages if m.error() is None]
            if not valid:
                continue
            result = pipeline.process_batch([m.value() for m in valid])
            for letter in result.dead_letters:
                dlq.produce(dlq_topic, value=json.dumps(letter.__dict__))
            dlq.flush()
            if result.committable:
                consumer.commit(asynchronous=False)
    finally:
        consumer.close()


def _build_sink():
    if os.environ.get("SNOWFLAKE_ACCOUNT"):
        import snowflake.connector  # noqa: PLC0415

        from src.sink import SnowflakeMergeSink  # noqa: PLC0415

        conn = snowflake.connector.connect(
            account=os.environ["SNOWFLAKE_ACCOUNT"],
            user=os.environ["SNOWFLAKE_USER"],
            password=os.environ["SNOWFLAKE_PASSWORD"],
            warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "RISK_WH"),
            database=os.environ.get("SNOWFLAKE_DATABASE", "RISK_DB"),
            schema=os.environ.get("SNOWFLAKE_SCHEMA", "PUBLIC"),
        )
        return SnowflakeMergeSink(conn)
    from src.sink import InMemorySink  # noqa: PLC0415

    return InMemorySink()


if __name__ == "__main__":
    main()
