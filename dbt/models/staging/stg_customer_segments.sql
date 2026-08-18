with source_data as (
    select
        segment_id,
        segment_code,
        segment_name,
        target_annual_revenue,
        created_at,
        _ingestion_batch_id,
        _ingested_at
    from {{ source('source', 'customer_segments') }}
)

select * from source_data
