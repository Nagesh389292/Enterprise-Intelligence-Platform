with source_data as (
    select
        telemetry_id,
        machine_id,
        temperature_c,
        vibration_rms,
        pressure_psi,
        power_kw,
        recorded_at,
        _ingestion_batch_id,
        _ingested_at
    from {{ source('source', 'machine_telemetry') }}
)

select * from source_data
