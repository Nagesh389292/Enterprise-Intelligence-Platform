with source_data as (
    select
        supplier_id,
        supplier_code,
        company_name,
        quality_rating,
        lead_time_days,
        country_code,
        _ingestion_batch_id,
        _ingested_at
    from {{ source('source', 'suppliers') }}
)

select * from source_data
