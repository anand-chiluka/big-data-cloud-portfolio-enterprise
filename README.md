# Big Data Cloud Portfolio

This repository is a cloud separated big data engineering portfolio. Each cloud provider has its own isolated implementation so AWS, Azure, GCP, and OCI services are not mixed in the same project. Shared technologies such as Kafka, Snowflake, PySpark, Flink, Python, and Java are used where they make sense.

The projects are written to look and feel like production engineering work from a senior engineer: clear ownership boundaries, idempotent processing, schema validation, observability, quality checks, incremental design, and disaster recovery notes.

Important use note: Review, run, and customize the code before publishing it as your public work. The files are intentionally written as strong starter implementations that you can extend with your own cloud accounts, datasets, metrics, and screenshots.

## Portfolio Coverage

| Area | Batch | Real time | Serverless | Non serverless | Core technologies |
| --- | --- | --- | --- | --- | --- |
| AWS | Glue, EMR, S3 | Kinesis, MSK, Flink | Lambda | EMR, MSK | PySpark, Flink, Kafka, Snowflake |
| Azure | Synapse, Databricks, ADLS | Event Hubs, Spark Streaming | Azure Functions | Databricks, Synapse | PySpark, Kafka compatible Event Hubs, Snowflake |
| GCP | Dataproc, BigQuery, GCS | Pub/Sub, Dataflow | Cloud Functions | Dataproc, Dataflow | Apache Beam, PySpark, Snowflake |
| OCI | OCI Data Flow, Object Storage | OCI Streaming | OCI Functions | Data Flow, Streaming | PySpark, Kafka protocol, Snowflake |
| Shared | Local sample data | Local Kafka | Docker Compose | Tests | Python, Java, Flink, Spark |

## Repository Layout

```text
big_data_cloud_portfolio/
  projects/
    aws/
    azure/
    gcp/
    oci/
  shared/
    python/
    java/
    kafka/
    flink/
    snowflake/
  data/
    sample/
    schemas/
  docs/
    architecture/
    challenges/
  tests/
  .github/workflows/
```

## How to Read This Repo as a Hiring Manager

1. Start with `docs/project_matrix.md` for the skill to project map.
2. Review one cloud folder based on the role, for example `projects/aws` for AWS roles.
3. Open each cloud README for the STAR story, design decisions, failure modes, and runbook.
4. Review `shared/python` for reusable engineering practices.
5. Review `docs/challenges/basic_medium_advanced.md` for interview ready talking points.

## Local Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python data/generators/generate_sample_data.py
pytest -q
```

Optional local stack:

```bash
docker compose up -d
```

## Design Themes

* Idempotent batch processing with deterministic partitioning.
* Real time event processing with backpressure, retries, and dead letter handling.
* Schema first ingestion for structured, semi structured, and unstructured inputs.
* Compression aware readers and writers for gzip, bz2, zip, parquet, and delta style layouts.
* Cloud isolated project boundaries.
* STAR descriptions embedded in READMEs and source file headers.
