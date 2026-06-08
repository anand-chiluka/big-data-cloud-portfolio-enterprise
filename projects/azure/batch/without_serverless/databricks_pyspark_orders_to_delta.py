"""
STAR
Situation: Partner order files arrive in ADLS and need curated Delta style tables for analytics.
Task: Build a non serverless Azure batch pipeline using Databricks or Synapse Spark.
Action: Read mixed raw inputs, enforce schema, add audit columns, and write partitioned curated data.
Result: Demonstrates Azure lakehouse batch processing with maintainable PySpark code.
"""

from __future__ import annotations

import argparse
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, StringType, StructField, StructType, TimestampType

from shared.python.spark_quality import assert_not_null, assert_required_columns
from shared.python.spark_session import build_spark

SCHEMA = StructType(
    [
        StructField("order_id", StringType(), False),
        StructField("customer_id", StringType(), False),
        StructField("order_ts", TimestampType(), True),
        StructField("amount", DoubleType(), True),
        StructField("currency", StringType(), True),
        StructField("channel", StringType(), True),
    ]
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="abfss path to raw order CSV files")
    parser.add_argument("--target", required=True, help="abfss path to curated Delta or parquet table")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    spark = build_spark("azure_orders_batch_delta")
    raw_df = spark.read.option("header", "true").schema(SCHEMA).csv(args.source)
    assert_required_columns(raw_df, ["order_id", "customer_id", "order_ts", "amount", "currency", "channel"])

    curated_df = (
        raw_df.withColumn("order_date", F.to_date("order_ts"))
        .withColumn("run_id", F.lit(args.run_id))
        .withColumn("ingested_at", F.current_timestamp())
        .withColumn("source_system", F.lit("azure_adls"))
    )
    assert_not_null(curated_df, ["order_id", "customer_id", "order_ts"])

    # Use format("delta") in a Databricks runtime. Parquet keeps this file runnable in plain Spark.
    curated_df.write.mode("overwrite").partitionBy("order_date").parquet(args.target)
    spark.stop()


if __name__ == "__main__":
    main()
