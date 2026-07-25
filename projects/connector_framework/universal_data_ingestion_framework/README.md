# Universal Multi-Source Data Ingestion Framework

## What this project is

A pluggable data ingestion framework demonstrating a single, consistent
pattern for extracting from every major category of data source a data
engineer encounters in practice, structured, semi-structured, and
unstructured, from traditional and cloud systems alike, and writing all
of it to any of four major cloud data platforms through the same
interface.

This is the connector architecture pattern real ingestion platforms
(Airbyte, Fivetran) are built on: a common contract between wildly
different source types, so adding a new source or a new destination
never requires rewriting the pipeline around it.

## Source types covered

| Category | Connector | What it demonstrates |
|---|---|---|
| Structured SQL | `SQLConnector` | Traditional and cloud RDBMS (PostgreSQL, SQL Server, Oracle, Aurora, Azure SQL, Cloud SQL); incremental extraction via high-water-mark cursor |
| NoSQL document | `NoSQLConnector` | MongoDB, DynamoDB, Cassandra, Cosmos DB; handling schema-variable, nested documents |
| REST API | `APIConnector` | Paginated third-party/internal APIs; created/updated/deleted sync reconciliation |
| Unstructured | `UnstructuredConnector` | PDF and plain text extraction, sentence-aware chunking for RAG/embedding pipelines |
| Batch files | `BatchFileConnector` | CSV, JSON, and Parquet file drops (vendor SFTP exports, nightly batch patterns) |
| Streaming | *(see companion project)* | Kafka event streaming with schema validation and enrichment: `../projects/shared_event_streaming/kafka_snowflake_risk_pipeline/` in this repo |

## Destination sinks covered

| Sink | Cloud | Write pattern |
|---|---|---|
| `SnowflakeSink` | Snowflake | Staged PUT + COPY INTO batch load |
| `AWSSink` | AWS | S3 object write, partitioned by date, for downstream Redshift COPY / Glue crawler / Snowpipe |
| `GCPSink` | GCP | BigQuery streaming insertAll |
| `AzureSink` | Azure | ADLS Gen2 file append, for downstream Synapse COPY INTO |
| `LocalSink` | none (filesystem) | Newline-delimited JSON to local disk; used by every test in this project |

## Architecture

```
Any BaseConnector (SQL / NoSQL / API / Unstructured / Batch)
        |
        v
ExtractedRecord (common envelope: source, category, id, payload, content_type)
        |
        v
Any BaseSink (Snowflake / AWS / GCP / Azure / Local)
        |
        v
orchestrator.run_pipeline() -- runs N connectors against 1 sink,
                                reports a per-source summary
```

Every connector returns the exact same `ExtractedRecord` shape regardless
of whether the source was a relational table, a MongoDB document, an API
response, or a PDF chunk. This is the design decision that matters most:
it means a sink implementation never needs to know or care which kind of
source produced the record it's writing.

## Design decisions

**One envelope, five very different sources.** The `content_type` field
(`structured` / `semi_structured` / `unstructured`) travels with every
record specifically so a downstream consumer, whether that's a Snowflake
table with a fixed schema or a vector store expecting embeddable text,
can branch on it without needing five different ingestion code paths.

**Incremental extraction is opt-in, not assumed.** `SQLConnector` and
`APIConnector` both support cursor-based incremental pulls; `NoSQLConnector`,
`UnstructuredConnector`, and `BatchFileConnector` intentionally do full
extraction each run, since documents, files, and PDFs are far more often
fully replaced or individually versioned than incrementally updated the
way a relational row is.

**Unstructured chunking breaks on sentence boundaries with overlap, not
fixed character counts.** A naive fixed-size split can cut a sentence in
half mid-thought, which measurably hurts embedding and retrieval quality.
Overlap between chunks means a fact sitting near a chunk boundary still
has full context in at least one chunk.

**API sync reconciliation, not naive re-ingestion.** `APIConnector`
tracks previous state and classifies every record as created, updated,
or deleted on each run, the same pattern used for CRM/billing/ERP
integrations where the source system rarely exposes a clean changelog.

## What has been validated, and what requires live credentials

Being direct about this, since it's the difference between a demo and a
production system:

**Actually run and tested in this environment**, no external credentials
required:
- All 5 connectors (`SQLConnector`, `NoSQLConnector`, `APIConnector`,
  `UnstructuredConnector`, `BatchFileConnector`)
- `LocalSink`
- The full orchestrator running all 5 connector types end-to-end against
  a real sink
- Unstructured extraction against a real, multi-paragraph PDF (not a
  mock), confirming actual text extraction and sentence-aware chunking
- Full pytest suite: **9/9 passing**, including incremental SQL cursor
  behavior and API created/updated/deleted sync logic

```
$ pytest tests/ -v
9 passed in 1.08s
```

**Written as correct, real SDK usage but NOT executed against live cloud
accounts**, since no Snowflake, AWS, GCP, or Azure credentials exist in
this environment:
- `SnowflakeSink`, `AWSSink`, `GCPSink`, `AzureSink` — each one's
  production code path (the real `snowflake-connector-python`, `boto3`,
  `google-cloud-bigquery`, and `azure-storage-file-datalake` calls) is
  written and documented in comments, and each sink raises a clear
  `NotImplementedError` rather than silently pretending to write to a
  cloud that isn't actually connected. Every test in this project uses
  `LocalSink` instead, specifically so nothing here overstates what's
  been verified.

For sinks that were fully exercised against real (if adjacent) tooling,
see the two companion projects in this repo: `dbt_snowflake_subscriptions/`
(validated with `dbt parse`/`dbt compile`, zero errors) and
`aws_snowflake_ingestion/` (Lambda ingestion logic actually run and
tested locally, 5/5 passing).

## Run it yourself

```bash
pip install -r requirements.txt
pytest tests/ -v
```

To see it run end-to-end with real output:

```python
from src.connectors import SQLConnector, build_demo_sqlite_source
from src.sinks import LocalSink
from src.orchestrator import run_pipeline

conn = build_demo_sqlite_source()
connector = SQLConnector(conn, table_name="customers")
sink = LocalSink("./output")
run_pipeline([connector], sink)
# check ./output/sql_customers.ndjson
```

## What I'd add next

A schema registry layer sitting between connectors and sinks, so a
schema change in any source (a new column, a renamed API field, a
restructured NoSQL document) gets caught and surfaced before it reaches
a sink, the same fail-fast validation principle used in the
`kafka_snowflake_risk_pipeline` companion project, generalized across
every source type here rather than just streaming.
