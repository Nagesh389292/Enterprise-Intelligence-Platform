with source_data as (
    select
        inventory_id,
        warehouse_id,
        product_id,
        quantity_on_hand,
        quantity_allocated,
        (quantity_on_hand - quantity_allocated) as quantity_available,
        last_count_date,
        _ingestion_batch_id,
        _ingested_at
    from {{ source('source', 'inventory') }}
)

select * from source_data
