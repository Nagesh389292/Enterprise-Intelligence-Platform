with source_data as (
    select
        customer_id,
        company_name,
        industry,
        segment_id,
        account_status,
        contact_email,
        contact_phone,
        credit_limit,
        created_at,
        updated_at,
        _ingestion_batch_id,
        _ingested_at
    from {{ source('source', 'customers') }}
)

select * from source_data
