{{ config(materialized='table') }}

with warehouses as (
    select * from {{ ref('stg_warehouses') }}
)

select
    warehouse_id,
    warehouse_code,
    warehouse_name,
    region,
    capacity_sqft,
    _ingested_at
from warehouses
