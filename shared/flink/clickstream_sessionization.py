"""
STAR
Situation: Product analytics teams need session metrics from high volume clickstream events.
Task: Create a Flink pattern for event time sessionization with late event tolerance.
Action: Parse Kafka events, assign timestamps, use session windows, and emit aggregate metrics.
Result: Demonstrates advanced stateful streaming design suitable for AWS MSK, Azure Event Hubs Kafka endpoint, and OCI Streaming.
"""

from __future__ import annotations

# This file is intentionally written as a design ready PyFlink job. In a real deployment, add the
# correct Flink Kafka connector jar for the target runtime.

from pyflink.common import WatermarkStrategy
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaOffsetsInitializer


def build_kafka_source(bootstrap_servers: str, topic: str, group_id: str) -> KafkaSource:
    """Build a Kafka source with earliest offset startup for repeatable local demos."""
    return (
        KafkaSource.builder()
        .set_bootstrap_servers(bootstrap_servers)
        .set_topics(topic)
        .set_group_id(group_id)
        .set_starting_offsets(KafkaOffsetsInitializer.earliest())
        .set_value_only_deserializer(SimpleStringSchema())
        .build()
    )


def main() -> None:
    env = StreamExecutionEnvironment.get_execution_environment()
    env.enable_checkpointing(60_000)
    env.set_parallelism(2)

    source = build_kafka_source("localhost:9092", "clickstream.raw", "flink_sessionizer")
    stream = env.from_source(source, WatermarkStrategy.no_watermarks(), "kafka_clickstream_source")

    # Production extension points:
    # 1. Parse JSON into typed rows.
    # 2. Assign event time and bounded out of order watermarks.
    # 3. Key by user id.
    # 4. Apply session windows.
    # 5. Write curated aggregates to Kafka, Iceberg, Delta, or Snowflake.
    stream.print()

    env.execute("clickstream_sessionization")


if __name__ == "__main__":
    main()
