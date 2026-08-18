{{ config(materialized='table') }}

with customers as (
    select * from {{ ref('stg_customers') }}
),

segments as (
    select * from {{ ref('stg_customer_segments') }}
),

addresses as (
    select distinct on (customer_id) *
    from {{ ref('stg_customer_addresses') }}
    order by customer_id, case when address_type = 'SHIPPING' then 1 else 2 end
)

select
    c.customer_id,
    c.company_name,
    c.industry,
    c.segment_id,
    s.segment_code,
    s.segment_name,
    c.account_status,
    c.contact_email,
    c.contact_phone,
    c.credit_limit,
    a.street_address as primary_street_address,
    a.city as primary_city,
    a.state_province as primary_state_province,
    a.postal_code as primary_postal_code,
    a.country_code as primary_country_code,
    -- SCD Type 2 Audit Columns (Initial Observed Snapshot)
    c.created_at as valid_from,
    cast(null as timestamp with time zone) as valid_to,
    true as is_current,
    1 as record_version,
    c._ingested_at
from customers c
left join segments s on c.segment_id = s.segment_id
left join addresses a on c.customer_id = a.customer_id
