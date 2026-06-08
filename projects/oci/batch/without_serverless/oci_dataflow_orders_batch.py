"""
STAR
Situation: OCI Object Storage files need curated analytics output for enterprise reporting and ML teams.
Task: Build a non serverless OCI Data Flow PySpark job.
Action: Read object storage data, validate required fields, add audit columns, and write partitioned parquet.
Result: Demonstrates OCI native big data engineering aligned with enterprise Fusion style workloads.
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
    parser.add_argument("--source", required=True, help="oci path such as oci://bucket@namespace/path")
    parser.add_argument("--target", required=True, help="oci curated output path")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    spark = build_spark("oci_dataflow_orders_batch")
    df = spark.read.option("header", "true").schema(SCHEMA).csv(args.source)
    curated = (
        df.withColumn("order_date", F.to_date("order_ts"))
        .withColumn("run_id", F.lit(args.run_id))
        .withColumn("ingested_at", F.current_timestamp())
        .withColumn("source_system", F.lit("oci_object_storage"))
    )
    assert_not_null(curated, ["order_id", "customer_id", "order_ts"])
    curated.write.mode("overwrite").partitionBy("order_date").parquet(args.target)
    spark.stop()


if __name__ == "__main__":
    main()
