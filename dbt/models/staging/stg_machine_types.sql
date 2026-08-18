with source_data as (
    select
        machine_type_id,
        type_name,
        manufacturer,
        max_temperature_c,
        max_vibration_rms,
        _ingestion_batch_id,
        _ingested_at
    from {{ source('source', 'machine_types') }}
)

select * from source_data
