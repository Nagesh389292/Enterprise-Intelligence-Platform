# Architecture Decision Record (ADR)

## ADR-005: Selection of a Hybrid dbt Core & PySpark Analytical Transformation Architecture

* **Status**: Accepted
* **Date**: 2026-08-17
* **Architect**: Antigravity Engineering Team
* **Deciders**: Enterprise Data Architecture Committee (NexaCore Industries)

---

## 1. Context and Problem Statement

NexaCore Industries has successfully ingested normalized enterprise data into the Silver layer (`source.*` schema in PostgreSQL).

To serve executive dashboards (Power BI), analytical reporting, predictive machine learning models, and domain AI agents, the platform requires an analytical transformation engine to construct the **Gold Layer (`analytics.*` schema)**.

The framework must handle two contrasting workload patterns:
1. **Relational Star Schema Transformations**: Joining normalized 3NF entity tables (`customers`, `orders`, `order_items`, `products`, `warehouses`, `suppliers`, `machines`) into clean dimensional models and transactional fact tables with complex business logic and SCD tracking.
2. **High-Volume Time-Series Telemetry Aggregation**: Processing high-frequency industrial IoT machine telemetry events (100,000+ raw records per run) into 1-minute rollup aggregates (`fact_machine_telemetry`).

---

## 2. Option Comparison

### Option A: Monolithic SQL Scripts / Custom Python ETL
* **Pros**: No external framework dependencies.
* **Cons**: No dependency DAG orchestration; lack of modular model testing or documentation; hard to maintain incremental refresh logic; high maintenance burden.

### Option B: Pure dbt Core (`dbt-postgres`)
* **Pros**: Modular SQL modeling (`staging` $\rightarrow$ `intermediate` $\rightarrow$ `marts`); built-in data documentation & testing (`unique`, `not_null`, `relationships`); native incremental models (`is_incremental()`).
* **Cons**: Single-node SQL execution on PostgreSQL host; heavy window aggregations on multi-million row time-series telemetry can bottleneck PostgreSQL CPU.

### Option C: Hybrid Architecture — dbt Core for Star Schema + PySpark for Time-Series Aggregations
* **Pros**: 
  * **dbt Core**: Industry-standard SQL modeling for all dimensions and relational facts (`fact_orders`, `fact_order_items`, `fact_inventory_daily`, `fact_support_tickets`).
  * **PySpark Engine**: Distributed Memory processing engine reserved for high-volume `machine_telemetry` window aggregations and feature store calculations.
* **Cons**: Requires maintaining both dbt SQL models and PySpark batch jobs.

---

## 3. Decision Outcome

**Chosen Option**: **Option C (Hybrid dbt Core + PySpark Architecture)**.

---

## 4. Rationale & Consequences

### Positive Consequences
- **Modular Data Lineage**: dbt provides automatic visual DAG lineage from `source.*` $\rightarrow$ `stg_*` $\rightarrow$ `int_*` $\rightarrow$ `dim_*` / `fact_*`.
- **High Performance at Scale**: PySpark handles heavy time-series aggregations without locking PostgreSQL relational tables.
- **Enterprise Test Coverage**: dbt schema tests enforce uniqueness, non-null, and referential integrity assertions before data reaches production dashboards.

### Negative Consequences
- Developers must maintain dbt project configs (`dbt_project.yml`) alongside PySpark scripts.
