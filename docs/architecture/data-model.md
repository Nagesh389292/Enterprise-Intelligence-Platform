# Data Architecture & Modeling Principles Specification
### NexaCore Enterprise Intelligence Platform

This document outlines the core data modeling principles, architectural patterns, timestamp handling, audit conventions, data quality enforcement, and scalability strategies for the **Enterprise Intelligence Platform (EIP)**.

---

## 1. Modeling Strategy: 3NF vs. Star Schema

The platform implements two distinct data modeling paradigms suited to their specific processing requirements:

```text
Operational Systems (OLTP)              Data Warehouse (OLAP)
   Normalized 3NF Model                 Dimensional Star Schema
┌───────────────────────────┐         ┌───────────────────────────┐
│ • High-frequency writes   │         │ • High-volume reads       │
│ • Zero redundancy         │  ETL    │ • Denormalized metrics    │
│ • Strict Integrity (PK/FK)├────────►│ • Surrogate Keys          │
│ • Optimized for updates   │         │ • Fast aggregation & JOINs│
└───────────────────────────┘         └───────────────────────────┘
```

1. **Normalized Source System Model (3NF)**:
   * Used in operational source systems and raw/staging databases.
   * Eliminates data redundancy, protects transactional integrity, enforces strict PK/FK constraints.
2. **Dimensional Analytical Model (Star Schema - Gold Layer)**:
   * Used in PostgreSQL Data Warehouse and dbt analytical layers.
   * Denormalized star schema composed of clear **Dimension Tables** (`dim_*`) and **Fact Tables** (`fact_*`).
   * Explicitly documented **Grain** per fact table.
   * Optimized for BI analytical queries, complex aggregations, window functions, and ML feature extraction.

---

## 2. Standardized Audit Columns & Lineage

Every table across raw staging, Silver processed, and Gold analytical tiers must incorporate standardized audit metadata to guarantee **end-to-end data lineage** and pipeline auditability:

| Audit Column | Data Type | Storage Tier | Description |
| :--- | :--- | :--- | :--- |
| `created_at` | TIMESTAMPTZ | Source / Silver / Gold | System timestamp when record was first inserted. |
| `updated_at` | TIMESTAMPTZ | Source / Silver | System timestamp when record was last updated. |
| `etl_batch_id` | VARCHAR(50) | Silver / Gold | Unique identifier of the pipeline job run that loaded the record. |
| `source_system` | VARCHAR(50) | Silver / Gold | Code identifying originating source system (e.g., `CRM_POSTGRES`, `IOT_STREAM`). |
| `is_quarantined` | BOOLEAN | Silver / Staging | Flag indicating if record failed data quality validation assertions. |

---

## 3. Timestamp & Timezone Standard

1. **UTC Standard**: All timestamp columns are strictly defined using `TIMESTAMPTZ` (Timestamp with Time Zone) and stored in **UTC (Coordinated Universal Time)**.
2. **ISO 8601 String Formatting**: Raw data text exports format timestamps strictly as `YYYY-MM-DDTHH:MM:SS.sssZ`.
3. **Date Dimension Integration**: All analytical facts contain integer surrogate keys (`date_key` formatted as `YYYYMMDD`) linked to `dim_date` to enable high-performance partition pruning and calendar filtering without timestamp parsing.

---

## 4. Scalability & High-Volume Partitioning Strategy

To support scale (millions of transactions and billions of telemetry signals), the storage architecture applies target partitioning strategies:

### 4.1 PostgreSQL Warehouse Table Partitioning
* **`fact_orders` & `fact_order_items`**: Range partitioned by `order_date_key` on a **Monthly** basis (`fact_orders_y2026m01`, `fact_orders_y2026m02`, etc.).
* **`fact_inventory_daily`**: Range partitioned by `date_key` on a **Monthly** basis.
* **`fact_machine_telemetry`**: Range partitioned by `date_key` on a **Daily / Weekly** basis to maintain index performance under high-velocity streaming inserts.

### 4.2 Lakehouse Storage Partitioning (Bronze / Silver Parquet)
* Storage paths in local/S3 data lake follow Hive-style directory partitioning:
  ```text
  data/raw/machine_telemetry/year=2026/month=08/day=17/
  data/processed/fact_orders/year=2026/month=08/
  ```

---

## 5. Data Quality Constraints & Quarantine Management

To prevent bad data from polluting downstream dashboards or corrupting machine learning feature sets, validation rules are applied during Bronze-to-Silver ETL:

```text
                      INCOMING RAW DATA
                              │
                              ▼
                     PySpark Validation Gate
                    (Schema & Rules Check)
                              │
               ┌──────────────┴──────────────┐
               │                             │
        Passes Assertions             Fails Assertions
               │                             │
               ▼                             ▼
          Silver Layer               Quarantine Table
       (Cleaned Datasets)            (Audited & Flagged)
               │
               ▼
           Gold DW
```

* **Validation Rules**:
  * **Null Checks**: Primary keys, order IDs, timestamps, customer IDs cannot be NULL.
  * **Range & Boundary Checks**: Prices > 0, Quantities > 0, Temperatures within -50°C to +300°C.
  * **Referential Integrity**: Order items must reference existing product SKUs.
* **Quarantine Handling**: Records failing any assertion are written to `data/processed/quarantine/` with an appended `quarantine_reason` string column detailing the failure rule.

---

## 6. Alignment with Downstream ML Requirements

The data model directly facilitates feature engineering for NexaCore's machine learning use cases:

1. **Customer Churn Model**: Supported by joining `dim_customers`, `fact_orders`, and `fact_support_tickets` to extract rolling 30/60/90-day order cadence, total spend, ticket frequency, and CSAT scores.
2. **Demand Forecasting Model**: Supported by querying `fact_order_items` and `fact_inventory_daily` grouped by `product_key`, `warehouse_key`, and `date_key` to build regular daily time-series.
3. **IoT Anomaly Detection**: Supported by querying aggregated minute-level metrics in `fact_machine_telemetry` alongside `dim_machines` specs.
