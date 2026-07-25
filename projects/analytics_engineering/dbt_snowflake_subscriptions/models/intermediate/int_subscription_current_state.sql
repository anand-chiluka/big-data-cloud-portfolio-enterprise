-- Intermediate: for each subscription, determine its current state
-- (active plan, amount, status) as of the latest event. This is the
-- kind of business logic that should live in exactly one place so
-- every downstream mart and every dashboard agrees on what "active"
-- and "current MRR" mean.

with events as (

    select * from {{ ref('stg_subscription_events') }}

),

ranked_events as (

    select
        *,
        row_number() over (
            partition by subscription_id
            order by event_at desc
        ) as rn_latest

    from events

),

current_state as (

    select
        subscription_id,
        customer_id,
        plan_code            as current_plan_code,
        amount_usd           as current_mrr_usd,
        event_type           as latest_event_type,
        event_at             as latest_event_at,
        case
            when event_type = 'canceled' then false
            else true
        end                   as is_active

    from ranked_events
    where rn_latest = 1

)

select * from current_state
