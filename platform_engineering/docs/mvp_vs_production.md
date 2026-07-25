# MVP vs. Production-Grade: What Changes and Why

A recurring question in any technical interview about this portfolio:
"this is a demo, what would you actually do differently in production?"
This document answers that directly and specifically, project by project,
rather than with generic platitudes.

## General principle

The gap between MVP and production is almost never "more features." It's
almost always: failure handling, observability, security, and the
operational muscle to run something reliably at 3am without you being
awake. Every "MVP" version in this repo intentionally cuts exactly these
corners, and this document is the honest list of what closing them looks
like.

## Kafka Risk Signal Pipeline

| Concern | MVP (what's in this repo) | Production |
|---|---|---|
| State management | In-process Python dict, single consumer | Stateful stream processor (Flink or Spark Structured Streaming) with checkpointing to durable storage; state survives a pod restart |
| Scaling | Single consumer instance | Partitioned consumer groups keyed by `account_id`, horizontally scaled via the HPA in `platform_engineering/kubernetes/` |
| Idempotency | In-memory upsert simulation | Real Snowflake `MERGE` statement keyed on `event_id`, safe under Kafka's at-least-once delivery |
| Dead letters | Logged and held in memory | Written to a real dead-letter Kafka topic + S3 prefix, with a replay tool for after a schema fix ships |
| Alerting | `monitor.py` logs pass/fail | Wired to PagerDuty/Opsgenie via the SLO checks in `platform_engineering/observability/` |

## dbt Subscription Metrics

| Concern | MVP | Production |
|---|---|---|
| Source freshness | Static seed CSVs | `dbt source freshness` checks with alerting when the raw tables go stale |
| Testing | 21 generic + 1 custom test | Add `dbt-expectations` package for statistical tests (distribution checks, outlier detection on MRR) |
| Deployment | Manual `dbt run` | Scheduled via the CronJob pattern in `platform_engineering/kubernetes/cronjob.yaml`, orchestrated by Airflow/Dagster with dbt Cloud or `dbt-core` in CI |
| Semantic layer | Plain SQL marts | MetricFlow / dbt Semantic Layer or Snowflake Semantic Views on top of `mart_company_mrr_summary`, so the same metric definition is queryable from any BI tool without redefinition |

## AWS -> Snowflake Ingestion

| Concern | MVP | Production |
|---|---|---|
| S3 write | Local filesystem stand-in | Real `boto3.put_object`, with multipart upload for files above 100MB |
| Secrets | Placeholders in Terraform variables | AWS Secrets Manager + Snowflake key-pair auth, never a static password in an env var |
| IAM | Single broad role | Least-privilege role scoped to exactly the S3 prefix and Snowflake schema needed, reviewed quarterly |
| Disaster recovery | None documented | Documented RPO/RTO, S3 cross-region replication for the landing zone, Snowflake Time Travel + Fail-safe retention policy explicitly set per table |

## Universal Ingestion Framework

| Concern | MVP | Production |
|---|---|---|
| Cloud sinks | Raise `NotImplementedError`, log the production code path | Real SDK calls, with retry/backoff and circuit breakers (see performance doc) |
| Schema evolution | Not handled | A schema registry (Confluent Schema Registry for Kafka, or a lightweight versioned JSON Schema store for the other connectors) with backward-compatibility enforcement before a producer can ship a breaking change |
| Connector configuration | Hardcoded in Python | Externalized to YAML/JSON config per connector instance, loaded at runtime, so adding a new SQL source doesn't require a code change, just a config entry |
| Orchestration | A simple for-loop in `orchestrator.py` | Airflow DAGs or Dagster assets, one task per connector, with per-task retries, alerting, and a dependency graph instead of a flat sequential loop |

## Governance Layer

| Concern | MVP | Production |
|---|---|---|
| PII detection | Regex patterns + field name hints | Add a trained NER model (e.g. Microsoft Presidio) for PII embedded in unstructured free text, which regex alone will always under-detect |
| Audit log storage | In-memory Python list | Append-only Snowflake table with insert-only grants, or a dedicated service (AWS CloudTrail, Azure Monitor), never a table the application itself can UPDATE or DELETE from |
| Role definitions | Hardcoded Python objects | Loaded from the identity provider's group membership (Okta/Azure AD) or a policy-as-code engine (Open Policy Agent), so access changes don't require a code deploy |
| Encryption | Not addressed | Encryption at rest (KMS-backed) on every sink, TLS in transit everywhere, and field-level encryption (not just masking) for the highest-sensitivity fields like SSN |
