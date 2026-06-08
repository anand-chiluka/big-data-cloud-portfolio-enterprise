"""
STAR
Situation: Curated warehouse tables need business level enrichment without moving data out of Snowflake.
Task: Build a Snowpark transformation that scores orders and writes an analytics ready table.
Action: Read curated orders, derive spend bands, aggregate customer metrics, and save as a managed table.
Result: Demonstrates Snowflake native transformation patterns that pair well with cloud lake ingestion.
"""

from __future__ import annotations

from snowflake.snowpark import Session
from snowflake.snowpark import functions as F


def build_customer_features(session: Session) -> None:
    """Create customer order features inside Snowflake using Snowpark."""
    orders = session.table("PORTFOLIO_BIG_DATA.CURATED.ORDER_SILVER")

    features = (
        orders.group_by("CUSTOMER_ID")
        .agg(
            F.count("ORDER_ID").alias("ORDER_COUNT"),
            F.sum("AMOUNT").alias("TOTAL_SPEND"),
            F.avg("AMOUNT").alias("AVG_ORDER_VALUE"),
            F.max("ORDER_TS").alias("LAST_ORDER_TS"),
        )
        .with_column(
            "SPEND_BAND",
            F.when(F.col("TOTAL_SPEND") >= F.lit(5000), F.lit("HIGH"))
            .when(F.col("TOTAL_SPEND") >= F.lit(1000), F.lit("MEDIUM"))
            .otherwise(F.lit("LOW")),
        )
    )

    features.write.mode("overwrite").save_as_table("PORTFOLIO_BIG_DATA.CURATED.CUSTOMER_FEATURES")
