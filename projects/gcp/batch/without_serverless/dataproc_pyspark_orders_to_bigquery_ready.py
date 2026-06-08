"""
STAR
Situation: GCS order data needs to be normalized before loading into BigQuery analytics tables.
Task: Build a non serverless Dataproc PySpark batch job.
Action: Read raw compressed CSV, validate fields, partition curated parquet, and prepare BigQuery ready output.
Result: Demonstrates GCP batch data engineering with Spark and warehouse aligned modeling.
"""

from __future__ import annotations

import argparse
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, StringType, StructField, StructType, TimestampType

from shared.python.spark_quality import assert_not_null
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
    parser.add_argument("--source", required=True, help="gs path to raw order files")
    parser.add_argument("--target", required=True, help="gs path to curated parquet")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    spark = build_spark("gcp_dataproc_orders_batch")
    df = spark.read.option("header", "true").schema(SCHEMA).csv(args.source)
    curated = (
        df.withColumn("order_date", F.to_date("order_ts"))
        .withColumn("run_id", F.lit(args.run_id))
        .withColumn("ingested_at", F.current_timestamp())
        .withColumn("source_system", F.lit("gcp_gcs"))
    )
    assert_not_null(curated, ["order_id", "customer_id", "order_ts"])
    curated.write.mode("overwrite").partitionBy("order_date").parquet(args.target)
    spark.stop()


if __name__ == "__main__":
    main()
