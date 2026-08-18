with source_data as (
    select
        category_id,
        category_name,
        parent_category_id,
        created_at,
        _ingestion_batch_id,
        _ingested_at
    from {{ source('source', 'product_categories') }}
)

select * from source_data
