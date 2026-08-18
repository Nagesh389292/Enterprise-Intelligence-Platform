with source_data as (
    select
        survey_id,
        ticket_id,
        score,
        feedback_text,
        submitted_at,
        _ingestion_batch_id,
        _ingested_at
    from {{ source('source', 'customer_satisfaction') }}
)

select * from source_data
