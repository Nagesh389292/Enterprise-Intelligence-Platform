{{ config(materialized='table') }}

with maintenance as (
    select * from {{ ref('stg_maintenance_events') }}
)

select
    maintenance_id,
    machine_id,
    cast(to_char(performed_at, 'YYYYMMDD') as integer) as date_key,
    maintenance_type,
    description,
    technician_name,
    performed_at,
    cost_usd,
    case
        when maintenance_type = 'Emergency' then 24.0
        when maintenance_type = 'Corrective' then 8.0
        when maintenance_type = 'Preventive' then 2.0
        else 4.0
    end as derived_downtime_hours,
    _ingested_at
from maintenance
