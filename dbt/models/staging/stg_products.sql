with source_data as (
    select
        product_id,
        sku,
        product_name,
        category_id,
        unit_cost,
        unit_price,
        reorder_point,
        is_active,
        created_at,
        _ingestion_batch_id,
        _ingested_at
    from {{ source('source', 'products') }}
)

select * from source_data
