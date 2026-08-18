{{ config(materialized='table') }}

with products as (
    select * from {{ ref('stg_products') }}
),

categories as (
    select * from {{ ref('stg_product_categories') }}
)

select
    p.product_id,
    p.sku,
    p.product_name,
    p.category_id,
    c.category_name,
    c.parent_category_id,
    p.unit_cost,
    p.unit_price,
    p.reorder_point,
    p.is_active,
    p.created_at,
    p._ingested_at
from products p
left join categories c on p.category_id = c.category_id
