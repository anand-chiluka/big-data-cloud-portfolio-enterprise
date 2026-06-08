"""
STAR
Situation: Product and finance teams need reliable daily order data from S3 for analytics and ML features.
Task: Build a non serverless AWS batch job that can run on EMR or Spark on EKS.
Action: Enforce schema, add audit columns, validate required fields, partition by order date, and write curated parquet.
Result: Demonstrates production style PySpark batch engineering with replay safety and quality gates.
"""

from __future__ import annotations

import argparse
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, StringType, StructField, StructType, TimestampType

from shared.python.config_loader import load_yaml_config
from shared.python.spark_quality import assert_not_null, assert_required_columns
from shared.python.spark_session import build_spark

ORDER_SCHEMA = StructType(
    [
        StructField("order_id", StringType(), False),
        StructField("customer_id", StringType(), False),
        StructField("order_ts", TimestampType(), True),
        StructField("amount", DoubleType(), True),
        StructField("currency", StringType(), True),
        StructField("channel", StringType(), True),
    ]
)


def transform_orders(source_df, run_id: str):
    """Normalize raw orders and add audit columns."""
    return (
        source_df.withColumn("order_date", F.to_date("order_ts"))
        .withColumn("amount", F.round(F.col("amount"), 2))
        .withColumn("run_id", F.lit(run_id))
        .withColumn("ingested_at", F.current_timestamp())
        .withColumn("source_system", F.lit("aws_s3"))
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    config = load_yaml_config(args.config, ["source_path", "target_path", "required_columns"])
    spark = build_spark("aws_orders_batch_lakehouse")

    # Spark automatically handles gzip CSV when the input files end with .gz.
    raw_df = spark.read.option("header", "true").schema(ORDER_SCHEMA).csv(config["source_path"])
    assert_required_columns(raw_df, config["required_columns"])

    curated_df = transform_orders(raw_df, args.run_id)
    assert_not_null(curated_df, ["order_id", "customer_id", "order_ts"], max_failed_rows=0)

    (
        curated_df.repartition("order_date")
        .write.mode("overwrite")
        .format(config.get("output_format", "parquet"))
        .partitionBy(*config.get("partition_columns", ["order_date"]))
        .save(config["target_path"])
    )

    spark.stop()


if __name__ == "__main__":
    main()
