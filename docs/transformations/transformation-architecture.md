# Transformation Framework Architecture
### NexaCore Enterprise Intelligence Platform

---

## 1. Medallion Silver-to-Gold Boundaries

The transformation engine operates between the Silver conformed relational layer (`source.*`) and the Gold analytical serving layer (`analytics.*`):

```text
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                             SILVER LAYER                                    │
 │                     PostgreSQL Schema: source.*                             │
 │   Normalized 3NF Entities (customers, orders, products, telemetry, etc.)   │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                         TRANSFORMATION ENGINE                               │
 │                                                                             │
 │ ┌───────────────────────────────────────┐ ┌───────────────────────────────┐ │
 │ │            dbt Core Models            │ │       PySpark Batch Engine    │ │
 │ │  SQL Staging -> Intermediate -> Marts │ │  1-Min Telemetry Aggregations │ │
 │ └───────────────────────────────────────┘ └───────────────────────────────┘ │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                              GOLD LAYER                                     │
 │                   PostgreSQL Schema: analytics.*                            │
 │   Star Schema Dimensional Models (6 Dimensions + 6 Fact Tables)             │
 └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. dbt Layering Standard

dbt models are organized into three strict functional tiers:

### 2.1 Staging Tier (`models/staging/`)
* **Purpose**: Clean, lightweight 1:1 view wrappers around `source.*` Silver tables.
* **Operations**: Rename columns to standard naming conventions, cast data types, standardize timestamps to UTC, handle missing values.
* **Materialization**: `view`.

### 2.2 Intermediate Tier (`models/intermediate/`)
* **Purpose**: Complex business logic, entity joins, RFM customer calculations, and metric rollups.
* **Operations**: Multi-table joins, aggregate calculations (`total_spent`, `support_ticket_count`), CTE abstractions.
* **Materialization**: `ephemeral` or `view`.

### 2.3 Marts Tier (`models/marts/`)
* **Purpose**: Production Gold star schema dimensions and fact tables located in the `analytics.*` database schema.
* **Operations**: Surrogate key generation (`dbt_utils.generate_surrogate_key`), final fact metric derivations, SCD tracking.
* **Materialization**: `table` or `incremental`.

---

## 3. PySpark Engine Integration Strategy

For high-volume sensor datasets (`source.machine_telemetry` containing 100,000+ raw records per batch):
* **Why PySpark**: Standard relational SQL joins over millions of telemetry timestamps consume high PostgreSQL CPU/Memory. PySpark distributes window processing across memory blocks.
* **PySpark Task**: Reads raw event rows from `source.machine_telemetry`, executes 1-minute aggregation windows (`avg_temperature`, `max_temperature`, `avg_vibration`, `max_vibration`, `pressure_psi`, `power_kw`), computes rolling z-score anomaly indicators, and writes conformed aggregate rows directly to `analytics.fact_machine_telemetry`.
