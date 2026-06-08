# Project Matrix

| Project | Situation | Task | Action | Result | Skills demonstrated |
| --- | --- | --- | --- | --- | --- |
| AWS batch without Lambda | Large daily order files land in S3 and need governed lakehouse ingestion | Build deterministic ETL with replay safety | PySpark normalizes, validates, partitions, and writes curated output | Repeatable batch pipeline with quality gates and audit fields | EMR, S3, PySpark, Parquet, Iceberg style design |
| AWS batch with Lambda | New S3 object should trigger serverless orchestration | Submit Glue job from event | Lambda validates payload and starts job with idempotency key | Event driven batch start with clear failure path | Lambda, Glue, S3 events, Python |
| AWS real time without Lambda | Payment events require low latency sessionization | Consume MSK topic and write enriched stream | Flink job manages event time, watermarks, late events, DLQ | Real time pipeline with backpressure design | Kafka, MSK, Flink, checkpoints |
| AWS real time with Lambda | Kinesis records need lightweight enrichment | Process events without managing servers | Lambda parses, enriches, emits failed records to DLQ | Small, cost effective event handler | Kinesis, Lambda, Python |
| Azure batch without Functions | Partner data lands in ADLS and powers analytics | Build Databricks or Synapse batch ETL | PySpark reads CSV JSON text, validates, writes Delta layout | Reusable Azure lakehouse pipeline | ADLS, PySpark, Delta pattern |
| Azure batch with Functions | Blob arrival should submit managed compute | Trigger Databricks job from blob event | Function extracts path and starts parameterized job | Decoupled ingestion and compute | Azure Functions, Blob, Databricks |
| Azure real time without Functions | Event Hubs stream supports product analytics | Spark Structured Streaming job | Exactly once style checkpointing and late event handling | Real time bronze to silver pattern | Event Hubs, Spark Streaming |
| Azure real time with Functions | Small event transformations need serverless route | Function receives Event Hub trigger | Validate, enrich, and route to storage or queue | Lightweight serverless streaming path | Event Hubs, Azure Functions |
| GCP batch without Functions | GCS files need BigQuery ready output | Dataproc PySpark batch | Normalize, quality check, write partitioned parquet | Batch lake to warehouse path | Dataproc, GCS, BigQuery |
| GCP batch with Functions | GCS finalize events should submit Dataproc | Cloud Function starts parameterized batch | Idempotency and run labels included | Serverless control plane | Cloud Functions, Dataproc |
| GCP real time without Functions | Pub/Sub events need analytic serving | Dataflow streaming pipeline | Beam validates, windows, writes BigQuery | Managed streaming dataflow | Pub/Sub, Dataflow, Beam |
| GCP real time with Functions | Pub/Sub events need simple enrichment | Cloud Function transforms events | Dead letter routing and schema checks | Serverless event processing | Pub/Sub, Cloud Functions |
| OCI batch without Functions | Object Storage files feed Fusion style analytics | OCI Data Flow PySpark job | Secrets, schema validation, output partitioning | Enterprise OCI batch foundation | OCI Data Flow, Object Storage, PySpark |
| OCI batch with Functions | Object create event triggers Data Flow | OCI Function starts application run | Path metadata and retry safe request | Serverless batch submission | OCI Functions, Data Flow |
| OCI real time without Functions | OCI Streaming events need stateful processing | Spark streaming consumes Kafka compatible stream | Checkpoints, watermarks, quality metrics | Real time OCI analytics path | OCI Streaming, Spark |
| OCI real time with Functions | Lightweight events need serverless enrichment | OCI Function transforms and forwards | Strong error handling and observability | Serverless OCI streaming | OCI Functions, Streaming |
