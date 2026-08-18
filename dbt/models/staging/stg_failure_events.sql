with source_data as (
    select
        failure_id,
        machine_id,
        failure_code,
        failure_reason,
        occurred_at,
        downtime_hours,
        _ingestion_batch_id,
        _ingested_at
    from {{ source('source', 'failure_events') }}
)

select * from source_data
