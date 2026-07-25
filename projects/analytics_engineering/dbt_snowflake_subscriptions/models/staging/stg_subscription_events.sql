-- Staging: clean, typed, one-to-one with the raw source table.
-- No business logic here, only renaming, type casting, and light cleanup.

with source as (

    select * from {{ ref('raw_subscription_events') }}

),

renamed as (

    select
        event_id,
        subscription_id,
        customer_id,
        lower(trim(event_type))            as event_type,
        cast(event_ts as timestamp)        as event_at,
        plan_code,
        (amount_cents / 100.0)::decimal(10,2) as amount_usd,
        upper(currency)                    as currency_code

    from source

)

select * from renamed
