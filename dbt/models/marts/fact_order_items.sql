{{ config(materialized='table') }}

with order_items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select order_id, order_timestamp from {{ ref('stg_orders') }}
),

products as (
    select product_id, unit_cost from {{ ref('stg_products') }}
)

select
    i.order_item_id,
    i.order_id,
    i.product_id,
    cast(to_char(o.order_timestamp, 'YYYYMMDD') as integer) as date_key,
    i.quantity,
    i.unit_price,
    i.discount_amount,
    p.unit_cost,
    (i.quantity * i.unit_price) as gross_revenue,
    i.total_price as net_revenue,
    (i.total_price - (i.quantity * p.unit_cost)) as gross_profit_margin,
    i._ingested_at
from order_items i
inner join orders o on i.order_id = o.order_id
inner join products p on i.product_id = p.product_id
