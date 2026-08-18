with source_data as (
    select
        ticket_id,
        ticket_number,
        customer_id,
        order_id,
        issue_category,
        priority,
        status,
        created_at,
        resolved_at,
        _ingestion_batch_id,
        _ingested_at
    from {{ source('source', 'support_tickets') }}
)

select * from source_data
