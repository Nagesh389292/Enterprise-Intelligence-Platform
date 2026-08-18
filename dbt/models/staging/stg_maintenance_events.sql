with source_data as (
    select
        maintenance_id,
        machine_id,
        maintenance_type,
        description,
        technician_name,
        performed_at,
        cost_usd,
        _ingestion_batch_id,
        _ingested_at
    from {{ source('source', 'maintenance_events') }}
)

select * from source_data
