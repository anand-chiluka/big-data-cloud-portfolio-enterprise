# S3 -> Lambda -> Snowpipe Ingestion Pipeline (AWS + Snowflake)

## What this project is

An event ingestion pipeline combining AWS (S3, Lambda, IAM, SQS via
Terraform) with Snowflake's auto-ingest Snowpipe, converting raw JSON
transaction events into validated, partitioned Parquet files that land in
S3 and are automatically picked up and loaded into Snowflake within
seconds of arrival, no manual COPY INTO or polling required.

## Architecture

```
Upstream event source (API Gateway / Kinesis / app)
        |
        v
Lambda: validate + convert to Parquet (lambda/ingest_handler.py)
        |
        v
S3 landing zone, partitioned by year/month/day (terraform/main.tf)
        |
        v
S3 event notification -> SQS queue (terraform/main.tf)
        |
        v
Snowpipe auto-ingest, triggered by SQS (sql/snowflake_setup.sql)
        |
        v
raw.transaction_events table in Snowflake
        |
        v
monitoring.pipe_ingestion_health view for on-call visibility
```

## Why this design

**Validation and Parquet conversion happen in Lambda, before S3, not in
Snowflake.** Rejecting malformed events at the edge means Snowpipe's
COPY INTO only ever sees clean, typed Parquet, and bad events are caught
with a clear reason and never appear as a confusing partial-load error
inside Snowflake's load history.

**Partitioning by year/month/day in the S3 key.** This isn't just
cosmetic; it lets S3 lifecycle rules expire old raw files automatically
(see the Terraform lifecycle configuration) and lets Snowflake's COPY
INTO prune scanned files by prefix if ever needed for a backfill.

**Auto-ingest via SQS notification, not a scheduled poll.** Using S3
event notifications feeding an SQS queue that Snowpipe listens to means
new data lands in Snowflake within seconds, not on the next poll
interval, which matters for the same reason real-time risk and fraud
signals matter: a five-minute-old signal is a much weaker signal.

**A dedicated monitoring view, not just relying on alerts.** `monitoring.pipe_ingestion_health`
surfaces file-level load success/error rates so on-call can diagnose an
ingestion problem by querying Snowflake directly, without digging through
raw Snowpipe history function syntax under time pressure.

## What has been validated, and what requires live cloud credentials

Being direct about this, since it matters for how this project should be
read:

**Actually run and tested in this environment:**
- `lambda/ingest_handler.py` — executed locally end-to-end. Sample batch
  of 4 events correctly validated (2 valid, 2 rejected with clear reasons
  for missing fields and bad types), converted to real Parquet bytes, and
  written to a local filesystem stand-in for S3. The Parquet output was
  read back with `pyarrow.parquet` and confirmed to contain correctly
  typed data.
- Full pytest suite (`tests/test_ingest_handler.py`), 5/5 passing,
  covering validation logic, Parquet round-tripping, and S3 key
  partitioning.

**Written as standard, correct syntax but NOT executed against live
infrastructure in this environment, since no AWS or Snowflake account
credentials are available here:**
- `terraform/main.tf` — standard, unmodified HashiCorp AWS provider HCL.
  The Terraform CLI itself was not available to run `terraform validate`
  in this environment; run that yourself before `terraform apply` as a
  sanity check.
- `sql/snowflake_setup.sql` — standard Snowflake DDL for a storage
  integration, external stage, and auto-ingest pipe. Requires a real
  Snowflake account and the AWS resources from Terraform to actually
  exist before it will run, since the storage integration's trust
  relationship is genuinely circular (each side needs the other's
  identifier), as noted in the SQL comments.

The honest summary: the application logic (the part most likely to have
actual bugs) is tested and proven to work. The infrastructure-as-code and
DDL are correct as written but unexercised, since doing so would require
real cloud credentials this environment doesn't have.

## Run the tested part yourself

```bash
pip install -r requirements.txt
cd lambda && python3 ingest_handler.py     # runs against local_s3_sim/ instead of real S3
cd .. && pytest tests/ -v
```

## Run the full pipeline live

1. `cd terraform && terraform init && terraform apply` (requires AWS credentials
   and a Snowflake storage integration IAM ARN, obtained via the two-pass
   process documented in `sql/snowflake_setup.sql`)
2. Run `sql/snowflake_setup.sql` against your Snowflake account, filling in
   the Terraform outputs
3. Wire `lambda/ingest_handler.py`'s `write_local` calls to real `boto3.client("s3").put_object(...)`
   calls and deploy as an actual Lambda function
4. Drop a test event through the pipeline and confirm it lands in
   `raw.transaction_events` within seconds

## What I'd add next

Dead-letter handling for the rejected-event path: currently rejected
events are only logged, not persisted anywhere queryable. In production
I'd write them to a `raw/_rejected/` S3 prefix in the same Parquet format,
so a data quality dashboard could track rejection rate and reasons over
time the same way `monitoring.pipe_ingestion_health` does for successful loads.
