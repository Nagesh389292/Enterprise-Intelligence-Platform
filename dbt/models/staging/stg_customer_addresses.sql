with source_data as (
    select
        address_id,
        customer_id,
        address_type,
        street_address,
        city,
        state_province,
        postal_code,
        country_code,
        is_primary,
        created_at,
        _ingestion_batch_id,
        _ingested_at
    from {{ source('source', 'customer_addresses') }}
)

select * from source_data
