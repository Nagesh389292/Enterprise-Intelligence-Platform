with source_data as (
    select
        order_id,
        order_number,
        customer_id,
        channel_id,
        shipping_address_id,
        order_status,
        order_timestamp,
        promised_delivery_date,
        total_amount,
        _ingestion_batch_id,
        _ingested_at
    from {{ source('source', 'orders') }}
)

select * from source_data
