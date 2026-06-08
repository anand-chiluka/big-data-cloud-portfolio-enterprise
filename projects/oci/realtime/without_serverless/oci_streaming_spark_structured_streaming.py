"""
STAR
Situation: OCI Streaming events need low latency analytics with checkpoint recovery.
Task: Build a non serverless Spark Structured Streaming job against OCI Streaming Kafka compatibility.
Action: Read Kafka protocol stream, parse JSON, validate event id, and write parquet with checkpoints.
Result: Demonstrates OCI real time engineering with familiar Spark streaming semantics.
"""

from __future__ import annotations

from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType, TimestampType

from shared.python.spark_session import build_spark

SCHEMA = StructType(
    [
        StructField("event_id", StringType(), False),
        StructField("event_type", StringType(), True),
        StructField("event_time", TimestampType(), True),
        StructField("source_system", StringType(), True),
        StructField("trace_id", StringType(), True),
    ]
)


def main() -> None:
    spark = build_spark("oci_streaming_spark")
    raw = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", "cell-1.streaming.us-ashburn-1.oci.oraclecloud.com:9092")
        .option("subscribe", "portfolio_events")
        .option("startingOffsets", "latest")
        .load()
    )
    parsed = raw.select(F.from_json(F.col("value").cast("string"), SCHEMA).alias("event")).select("event.*")
    valid = parsed.filter(F.col("event_id").isNotNull()).withWatermark("event_time", "10 minutes")

    query = (
        valid.writeStream.format("parquet")
        .option("path", "oci://curated@namespace/events")
        .option("checkpointLocation", "oci://checkpoints@namespace/events")
        .outputMode("append")
        .start()
    )
    query.awaitTermination()


if __name__ == "__main__":
    main()
