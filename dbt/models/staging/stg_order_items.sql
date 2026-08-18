with source_data as (
    select
        order_item_id,
        order_id,
        product_id,
        quantity,
        unit_price,
        discount_amount,
        total_price,
        _ingestion_batch_id,
        _ingested_at
    from {{ source('source', 'order_items') }}
)

select * from source_data
