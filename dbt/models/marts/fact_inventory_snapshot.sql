{{ config(materialized='table') }}

with inventory as (
    select * from {{ ref('stg_inventory') }}
),

products as (
    select product_id, reorder_point from {{ ref('stg_products') }}
)

select
    i.inventory_id,
    i.warehouse_id,
    i.product_id,
    cast(to_char(i.last_count_date, 'YYYYMMDD') as integer) as date_key,
    i.last_count_date as snapshot_timestamp,
    i.quantity_on_hand,
    i.quantity_allocated,
    i.quantity_available,
    p.reorder_point,
    case
        when i.quantity_available < p.reorder_point then true
        else false
    end as is_below_reorder_point,
    i._ingested_at
from inventory i
inner join products p on i.product_id = p.product_id
