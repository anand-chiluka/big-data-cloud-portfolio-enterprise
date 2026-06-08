# Basic, Medium, and Advanced Challenges

Each challenge is written in STAR format so it can be reused in interviews, GitHub descriptions, and recruiter conversations.

## Basic Challenges

### File: `shared/python/compression_registry.py`

**Situation:** Data arrived from partners in gzip, bz2, zip, and plain text formats.

**Task:** Provide one safe utility to detect and open common compressed files without scattering format checks across every job.

**Action:** Built a registry based reader that selects the correct Python standard library opener by file extension and exposes a simple iterator.

**Result:** Reduced duplicated ingestion code and made new file support easier to add.

### File: `shared/python/data_quality.py`

**Situation:** Batch and streaming jobs needed consistent checks for required columns, null thresholds, duplicate keys, and basic value ranges.

**Task:** Create reusable validation helpers that can run locally or inside Spark driver logic.

**Action:** Implemented quality rules with clear exceptions and human readable messages.

**Result:** Improved fail fast behavior and made pipeline failures easier to debug.

## Medium Challenges

### File: `projects/aws/batch/without_lambda/emr_pyspark_orders_to_lakehouse.py`

**Situation:** Daily order data landed in S3 across mixed formats and needed reliable lakehouse output.

**Task:** Build an idempotent PySpark batch pipeline with schema enforcement and partitioned output.

**Action:** Added explicit schema, audit columns, deterministic run id handling, validation, repartition strategy, and curated writes.

**Result:** Created a repeatable production style batch ETL pattern suitable for EMR, Glue, or Spark on Kubernetes.

### File: `projects/azure/realtime/without_functions/eventhub_spark_streaming.py`

**Situation:** Real time product events needed low latency downstream analytics with checkpoint recovery.

**Task:** Build a Spark Structured Streaming job for Event Hubs using event time processing.

**Action:** Implemented parsing, schema validation, watermarking, output checkpointing, and dead letter separation.

**Result:** Demonstrated reliable stream processing with recoverability and late event handling.

## Advanced Challenges

### File: `projects/aws/realtime/without_lambda/msk_flink_sessionizer.py`

**Situation:** High volume clickstream events required sessionization and backpressure aware processing.

**Task:** Use Flink to perform event time session windows over Kafka records.

**Action:** Designed Kafka source and sink, event time assignment, watermark strategy, session windows, checkpointing, and DLQ routing.

**Result:** Showed advanced stateful streaming design with operational resilience.

### File: `shared/snowflake/sql/streams_tasks_dynamic_tables.sql`

**Situation:** Cloud lake outputs needed warehouse side incremental processing without reprocessing full history.

**Task:** Build a Snowflake pattern using stages, file formats, streams, tasks, and merge logic.

**Action:** Created schema objects for staged data, incremental change capture, validation, and curated merges.

**Result:** Demonstrated a stable lake to warehouse architecture with managed incremental refresh.

### File: `projects/gcp/realtime/without_functions/dataflow_pubsub_to_bigquery.py`

**Situation:** Pub/Sub events needed scalable managed streaming with analytical serving in BigQuery.

**Task:** Implement Apache Beam streaming with windowing, validation, and DLQ.

**Action:** Built event parser, fixed window aggregation, BigQuery writes, and bad record side outputs.

**Result:** Created a portable GCP streaming pattern with production grade failure handling.
