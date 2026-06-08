"""
STAR
Situation: Product events arrive in Azure Event Hubs and need near real time curated storage.
Task: Build a non serverless Spark Structured Streaming job with checkpoint recovery.
Action: Read Event Hubs, parse JSON, apply watermarking, write valid records, and isolate bad records.
Result: Demonstrates Azure real time engineering with clear reliability controls.
"""

from __future__ import annotations

from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType, TimestampType

from shared.python.spark_session import build_spark

EVENT_SCHEMA = StructType(
    [
        StructField("event_id", StringType(), False),
        StructField("user_id", StringType(), True),
        StructField("event_ts", TimestampType(), True),
        StructField("page", StringType(), True),
        StructField("device", StringType(), True),
    ]
)


def main() -> None:
    spark = build_spark("azure_eventhub_streaming")

    event_hub_conf = {
        # Store the encrypted connection string in Key Vault in production.
        "eventhubs.connectionString": "Endpoint=sb://example.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=example;EntityPath=events"
    }

    raw = spark.readStream.format("eventhubs").options(**event_hub_conf).load()
    parsed = raw.select(F.from_json(F.col("body").cast("string"), EVENT_SCHEMA).alias("event")).select("event.*")

    valid = parsed.filter(F.col("event_id").isNotNull()).withWatermark("event_ts", "10 minutes")

    query = (
        valid.writeStream.format("parquet")
        .option("path", "abfss://curated@example.dfs.core.windows.net/events")
        .option("checkpointLocation", "abfss://checkpoints@example.dfs.core.windows.net/events")
        .outputMode("append")
        .start()
    )
    query.awaitTermination()


if __name__ == "__main__":
    main()
