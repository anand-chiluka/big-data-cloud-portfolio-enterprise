-- Target table for the idempotent MERGE sink. event_id is the natural idempotency key.
CREATE TABLE IF NOT EXISTS RISK_SIGNALS (
  event_id              STRING        NOT NULL,
  event_time            TIMESTAMP_TZ  NOT NULL,
  account_id            STRING        NOT NULL,
  merchant_id           STRING        NOT NULL,
  device_id             STRING        NOT NULL,
  country               STRING        NOT NULL,
  currency              STRING        NOT NULL,
  amount                NUMBER(18,2)  NOT NULL,
  tx_count_5m           NUMBER        NOT NULL,
  amount_sum_5m         NUMBER(18,2)  NOT NULL,
  distinct_countries_1h NUMBER        NOT NULL,
  is_new_device         BOOLEAN       NOT NULL,
  risk_flags            VARIANT,
  risk_score            NUMBER        NOT NULL,
  PRIMARY KEY (event_id)  -- informational in Snowflake; uniqueness is enforced by the MERGE, not the constraint
);
