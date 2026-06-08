# Reliability Principles

## Idempotency

Every batch job accepts a run id and deterministic source path. Curated outputs include `run_id`, `ingested_at`, and source metadata. In production, replace overwrite examples with merge into Iceberg, Delta, Hudi, or Snowflake tables.

## Backpressure

Streaming jobs separate heavy enrichment from lightweight routing. Flink and Spark examples include checkpointing and watermarks. Serverless examples are intentionally small and route failures to dead letter destinations.

## Observability

Each source file uses structured logging fields such as pipeline, environment, cloud, run id, input path, output path, and record count. In real deployments, send these logs to CloudWatch, Azure Monitor, Cloud Logging, OCI Logging, or OpenTelemetry collectors.

## Data Quality

Validation happens early at ingestion and again before curated writes. Invalid records should not silently disappear. They are routed to quarantine or DLQ paths with a reason code.
