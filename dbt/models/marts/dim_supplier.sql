{{ config(materialized='table') }}

with suppliers as (
    select * from {{ ref('stg_suppliers') }}
)

select
    supplier_id,
    supplier_code,
    company_name,
    quality_rating,
    lead_time_days,
    country_code,
    _ingested_at
from suppliers
