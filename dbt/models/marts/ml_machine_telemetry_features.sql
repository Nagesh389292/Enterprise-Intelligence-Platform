{{ config(materialized='table') }}

/*
  NexaCore ML Feature Mart: Machine Telemetry Anomaly Detection
  Grain: 1 row per machine x 1-minute interval (29,800 rows)
  Temporal Anti-Leakage Constraint:
    Rolling 10-minute feature windows use ROWS BETWEEN 10 PRECEDING AND CURRENT ROW
    to prevent temporal leakage across sensor intervals.
*/

WITH telemetry_base AS (
    SELECT
        t.telemetry_minute_key,
        t.machine_id,
        m.machine_type_name,
        m.warehouse_id,
        w.warehouse_name,
        t.minute_timestamp,
        t.event_count AS raw_event_count,
        t.avg_temperature_c,
        t.max_temperature_c,
        t.avg_vibration_rms,
        t.max_vibration_rms,
        t.avg_pressure_psi,
        t.avg_power_kw,
        (t.max_temperature_c - t.avg_temperature_c) AS temp_spread
    FROM {{ ref('fact_machine_telemetry') }} t
    JOIN {{ ref('dim_machine') }} m ON t.machine_id = m.machine_id
    JOIN {{ ref('dim_warehouse') }} w ON m.warehouse_id = w.warehouse_id
),

rolling_features AS (
    SELECT
        tb.*,
        AVG(tb.avg_temperature_c) OVER (
            PARTITION BY tb.machine_id ORDER BY tb.minute_timestamp
            ROWS BETWEEN 10 PRECEDING AND CURRENT ROW
        ) AS rolling_10min_avg_temp,
        AVG(tb.avg_vibration_rms) OVER (
            PARTITION BY tb.machine_id ORDER BY tb.minute_timestamp
            ROWS BETWEEN 10 PRECEDING AND CURRENT ROW
        ) AS rolling_10min_avg_vib
    FROM telemetry_base tb
)

SELECT
    rf.telemetry_minute_key,
    rf.machine_id,
    rf.machine_type_name,
    rf.warehouse_id,
    rf.warehouse_name,
    rf.minute_timestamp,
    rf.raw_event_count,
    rf.avg_temperature_c,
    rf.max_temperature_c,
    ROUND(rf.temp_spread, 2) AS temp_spread,
    rf.avg_vibration_rms,
    rf.max_vibration_rms,
    rf.avg_pressure_psi,
    rf.avg_power_kw,
    ROUND(COALESCE(rf.rolling_10min_avg_temp, rf.avg_temperature_c), 2) AS rolling_10min_avg_temp,
    ROUND(COALESCE(rf.rolling_10min_avg_vib, rf.avg_vibration_rms), 2) AS rolling_10min_avg_vib,
    -- Composite Anomaly Severity Score (Normalized Z-score proxy for anomaly flagging)
    ROUND((
        CASE WHEN rf.avg_temperature_c > 85.0 THEN 2.0 ELSE 0.0 END +
        CASE WHEN rf.avg_vibration_rms > 3.5 THEN 2.0 ELSE 0.0 END +
        CASE WHEN rf.avg_pressure_psi > 1500.0 THEN 1.0 ELSE 0.0 END
    )::NUMERIC, 2) AS anomaly_severity_score
FROM rolling_features rf
