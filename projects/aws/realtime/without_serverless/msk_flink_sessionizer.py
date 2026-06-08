"""
STAR
Situation: Clickstream events in MSK need stateful session metrics for product analytics.
Task: Build a non serverless streaming job with event time processing and checkpoint recovery.
Action: Use Flink Kafka source, checkpointing, and placeholders for watermarks, session windows, and DLQ routing.
Result: Demonstrates advanced real time design for high throughput AWS Kafka workloads.
"""

from __future__ import annotations

from shared.flink.clickstream_sessionization import main

# This AWS specific entrypoint intentionally reuses the cloud neutral Flink sessionization pattern.
# In production, configure bootstrap servers to MSK brokers, checkpoint storage to S3, and sinks to
# Iceberg, OpenSearch, Redshift, or Snowflake based on the consuming workload.

if __name__ == "__main__":
    main()
