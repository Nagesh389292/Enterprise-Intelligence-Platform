{{ config(materialized='table') }}

with machines as (
    select * from {{ ref('stg_machines') }}
),

machine_types as (
    select * from {{ ref('stg_machine_types') }}
),

warehouses as (
    select * from {{ ref('stg_warehouses') }}
)

select
    m.machine_id,
    m.serial_number,
    m.machine_type_id,
    mt.type_name as machine_type_name,
    mt.manufacturer,
    mt.max_temperature_c,
    mt.max_vibration_rms,
    m.warehouse_id,
    w.warehouse_code,
    w.warehouse_name,
    w.region as warehouse_region,
    m.installation_date,
    m.status as machine_status,
    m._ingested_at
from machines m
left join machine_types mt on m.machine_type_id = mt.machine_type_id
left join warehouses w on m.warehouse_id = w.warehouse_id
