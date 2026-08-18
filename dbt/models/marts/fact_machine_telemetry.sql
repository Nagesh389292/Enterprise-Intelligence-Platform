{{ config(materialized='table') }}

with raw_telemetry as (
    select * from {{ ref('stg_machine_telemetry') }}
),

machines as (
    select machine_id, machine_type_id from {{ ref('stg_machines') }}
),

machine_types as (
    select machine_type_id, max_temperature_c, max_vibration_rms from {{ ref('stg_machine_types') }}
),

minute_aggregates as (
    select
        t.machine_id,
        date_trunc('minute', t.recorded_at) as minute_timestamp,
        count(*) as event_count,
        avg(t.temperature_c) as avg_temperature_c,
        max(t.temperature_c) as max_temperature_c,
        min(t.temperature_c) as min_temperature_c,
        avg(t.vibration_rms) as avg_vibration_rms,
        max(t.vibration_rms) as max_vibration_rms,
        avg(t.pressure_psi) as avg_pressure_psi,
        avg(t.power_kw) as avg_power_kw
    from raw_telemetry t
    group by t.machine_id, date_trunc('minute', t.recorded_at)
)

select
    md5(concat(a.machine_id::text, '_', to_char(a.minute_timestamp, 'YYYY-MM-DD HH24:MI:SS'))) as telemetry_minute_key,
    a.machine_id,
    cast(to_char(a.minute_timestamp, 'YYYYMMDD') as integer) as date_key,
    a.minute_timestamp,
    a.event_count,
    a.avg_temperature_c,
    a.max_temperature_c,
    a.min_temperature_c,
    a.avg_vibration_rms,
    a.max_vibration_rms,
    a.avg_pressure_psi,
    a.avg_power_kw,
    mt.max_temperature_c as type_max_temperature_c,
    mt.max_vibration_rms as type_max_vibration_rms,
    case
        when a.max_temperature_c > mt.max_temperature_c then true
        else false
    end as temperature_anomaly_flag,
    case
        when a.max_vibration_rms > mt.max_vibration_rms then true
        else false
    end as vibration_anomaly_flag
from minute_aggregates a
left join machines m on a.machine_id = m.machine_id
left join machine_types mt on m.machine_type_id = mt.machine_type_id
