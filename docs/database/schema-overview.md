# Schema Overview & Data Model Mapping
### NexaCore Enterprise Intelligence Platform

---

## 1. Schema Classification & Purpose

### 1.1 `source` Schema (Operational 3NF)
* **Purpose**: Replicates operational OLTP databases and landed event tables.
* **Characteristics**: Highly normalized (3NF), strict primary/foreign key constraints, non-null assertions, and raw un-aggregated telemetry event streams.
* **Table Count**: 18 tables across Customer, Sales, Supply Chain, Operations/IoT, and Support domains.

### 1.2 `staging` Schema (ETL Buffer Tier)
* **Purpose**: Transient landing layer used by PySpark and dbt during Silver/Gold transformations.
* **Characteristics**: Schema-aligned unindexed temporary tables cleared after pipeline execution runs.

### 1.3 `analytics` Schema (Gold Star Schema)
* **Purpose**: Production data warehouse layer serving BI reporting (Power BI) and machine learning feature extraction.
* **Characteristics**: Dimensional star schema (`dim_*` and `fact_*`) using integer surrogate keys.
* **Table Count**: 6 Dimension tables (`dim_customer`, `dim_product`, `dim_supplier`, `dim_warehouse`, `dim_machine`, `dim_date`) and 6 Fact tables (`fact_orders`, `fact_order_items`, `fact_inventory_daily`, `fact_machine_telemetry`, `fact_maintenance_events`, `fact_support_tickets`).

### 1.4 `audit` Schema (Governance & Lineage)
* **Purpose**: System-wide governance, data pipeline batch execution tracking, data quality test assertion results, and raw record quarantine storage.
* **Table Count**: 3 tables (`pipeline_execution_logs`, `data_quality_audit_logs`, `quarantine_records`).

---

## 2. Special Architectural Distinction: Machine Telemetry

A critical design requirement is the separation of **Raw High-Frequency Telemetry** vs. **Aggregated Analytical Telemetry**:

```text
       RAW STREAMING / LANDED SENSORS                    GOLD ANALYTICAL WAREHOUSE
      ┌───────────────────────────────┐               ┌───────────────────────────────┐
      │   source.machine_telemetry    │               │analytics.fact_machine_telem...│
      ├───────────────────────────────┤               ├───────────────────────────────┤
      │ telemetry_id (BIGINT PK)      │               │ telemetry_fact_key (BIGINT PK)│
      │ machine_id (UUID FK)          │               │ machine_key (INT FK)          │
      │ temperature_c (NUMERIC)       │  PySpark ETL  │ timestamp_minute (TIMESTAMPTZ)│
      │ vibration_rms (NUMERIC)       ├──────────────►│ avg_temperature_c             │
      │ pressure_psi (NUMERIC)        │ 1-Min Aggs    │ max_temperature_c             │
      │ power_kw (NUMERIC)            │               │ avg_vibration_rms             │
      │ recorded_at (TIMESTAMPTZ)     │               │ max_vibration_rms             │
      └───────────────────────────────┘               │ reading_count                 │
                                                      └───────────────────────────────┘
```

* **`source.machine_telemetry`**: Stores raw, individual sensor metric events at millisecond/second resolution. Essential for granular time-series analysis and root-cause failure investigation.
* **`analytics.fact_machine_telemetry`**: Stores pre-aggregated 1-minute statistics (`avg`, `max`, `count`) joined to `dim_machine` and `dim_date`. Essential for fast ML anomaly detection feature extraction and BI dashboards.
