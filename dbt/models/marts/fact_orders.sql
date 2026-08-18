{{ config(materialized='table') }}

with orders as (
    select * from {{ ref('stg_orders') }}
)

select
    order_id,
    order_number,
    customer_id,
    shipping_address_id,
    channel_id,
    order_status,
    order_timestamp,
    cast(to_char(order_timestamp, 'YYYYMMDD') as integer) as date_key,
    promised_delivery_date,
    -- Derived synthetic delivery date (labeled explicitly as synthetic derived metric)
    (order_timestamp + interval '3 days')::timestamp with time zone as derived_actual_delivery_date,
    case
        when promised_delivery_date is not null then
            extract(day from ((order_timestamp + interval '3 days') - promised_delivery_date::timestamp with time zone))::integer
        else null
    end as derived_delivery_delay_days,
    total_amount,
    _ingested_at
from orders
