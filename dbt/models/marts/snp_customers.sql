{{ config(materialized='table') }}

with current_customers as (
    select * from {{ ref('dim_customer') }}
)

select
    md5(concat(customer_id::text, '_v1')) as customer_sk,
    customer_id,
    company_name,
    industry,
    segment_id,
    segment_name,
    account_status,
    contact_email,
    contact_phone,
    credit_limit,
    primary_city,
    primary_state_province,
    primary_postal_code,
    primary_country_code,
    -- Effective validity window
    valid_from as effective_start_date,
    null::timestamp with time zone as effective_end_date,
    true as is_current,
    1 as record_version,
    _ingested_at
from current_customers
