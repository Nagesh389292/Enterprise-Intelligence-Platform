with source_data as (
    select
        machine_id,
        serial_number,
        machine_type_id,
        warehouse_id,
        installation_date,
        status,
        _ingestion_batch_id,
        _ingested_at
    from {{ source('source', 'machines') }}
)

select * from source_data
