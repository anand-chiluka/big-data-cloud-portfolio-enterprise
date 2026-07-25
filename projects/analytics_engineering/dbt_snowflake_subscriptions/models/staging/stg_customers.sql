with source as (

    select * from {{ ref('raw_customers') }}

),

renamed as (

    select
        customer_id,
        cast(signup_date as date) as signup_date,
        upper(country)            as country_code,
        acquisition_channel

    from source

)

select * from renamed
