with source_data as (
    select
        warehouse_id,
        warehouse_code,
        warehouse_name,
        region,
        capacity_sqft,
        _ingestion_batch_id,
        _ingested_at
    from {{ source('source', 'warehouses') }}
)

select * from source_data
