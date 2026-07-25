-- Snowflake-side setup for the S3 -> Snowpipe auto-ingestion pipeline.
-- Run this after the Terraform in ../terraform/ has been applied, using
-- the outputs (landing_bucket_name, snowpipe_notification_queue_arn) to
-- fill in the placeholders below.

-- 1. Storage integration: the trust relationship between Snowflake and
--    the AWS IAM role created in Terraform.
CREATE STORAGE INTEGRATION IF NOT EXISTS risk_events_s3_integration
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'S3'
  ENABLED = TRUE
  STORAGE_AWS_ROLE_ARN = '<snowflake_ingestion_role_arn from terraform output>'
  STORAGE_ALLOWED_LOCATIONS = ('s3://risk-events-landing-prod/raw/');

-- After creating the integration, run:
--   DESC INTEGRATION risk_events_s3_integration;
-- and copy the STORAGE_AWS_IAM_USER_ARN and STORAGE_AWS_EXTERNAL_ID
-- values back into the Terraform variable
-- `snowflake_storage_integration_iam_arn` before applying Terraform,
-- since the trust relationship is circular (each side needs the other's
-- identifier) and is normally set up in two passes.

-- 2. File format for the Parquet files landing in S3.
CREATE FILE FORMAT IF NOT EXISTS parquet_format
  TYPE = 'PARQUET';

-- 3. External stage pointing at the S3 landing zone.
CREATE STAGE IF NOT EXISTS risk_events_stage
  URL = 's3://risk-events-landing-prod/raw/'
  STORAGE_INTEGRATION = risk_events_s3_integration
  FILE_FORMAT = parquet_format;

-- 4. Target table the pipe loads into.
CREATE TABLE IF NOT EXISTS raw.transaction_events (
    event_id            STRING,
    account_id           STRING,
    amount               NUMBER(12,2),
    currency             STRING,
    event_ts             TIMESTAMP_NTZ,
    merchant_category     STRING,
    country               STRING,
    device_id             STRING,
    _loaded_at            TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _source_file          STRING,
    _source_file_row_number NUMBER
);

-- 5. Snowpipe: auto-ingests any new file landing in the stage, triggered
--    by the SQS notification queue Terraform configured on the S3 bucket.
CREATE PIPE IF NOT EXISTS risk_events_pipe
  AUTO_INGEST = TRUE
AS
COPY INTO raw.transaction_events (
    event_id, account_id, amount, currency, event_ts,
    merchant_category, country, device_id, _source_file, _source_file_row_number
)
FROM (
    SELECT
        $1:event_id::STRING,
        $1:account_id::STRING,
        $1:amount::NUMBER(12,2),
        $1:currency::STRING,
        $1:event_ts::TIMESTAMP_NTZ,
        $1:merchant_category::STRING,
        $1:country::STRING,
        $1:device_id::STRING,
        METADATA$FILENAME,
        METADATA$FILE_ROW_NUMBER
    FROM @risk_events_stage
)
FILE_FORMAT = parquet_format
ON_ERROR = 'SKIP_FILE_10%';   -- abort and alert if more than 10% of a file's rows fail to load

-- After running this, register the pipe's notification channel ARN
-- (SHOW PIPES; -> notification_channel column) as the SQS queue ARN
-- output by Terraform, so S3 object-created events actually trigger
-- ingestion. This wiring step is done once per pipe.

-- 6. Monitoring view: lets on-call quickly check ingestion health
--    without digging through Snowpipe's raw history function each time.
CREATE VIEW IF NOT EXISTS monitoring.pipe_ingestion_health AS
SELECT
    file_name,
    row_count,
    row_parsed,
    error_count,
    (error_count::FLOAT / NULLIF(row_parsed, 0)) AS error_rate,
    last_load_time
FROM TABLE(
    INFORMATION_SCHEMA.COPY_HISTORY(
        table_name => 'raw.transaction_events',
        start_time => DATEADD('hours', -24, CURRENT_TIMESTAMP())
    )
)
ORDER BY last_load_time DESC;
