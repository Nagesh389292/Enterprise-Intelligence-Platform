# Ingestion Observability, Audit Logging & Monitoring
### NexaCore Enterprise Intelligence Platform

---

## 📌 Architectural Overview

The **Ingestion Observability Layer** provides real-time visibility into pipeline health, data quality pass rates, ingestion throughput, and quarantine error distributions using dedicated tables in the `audit` schema.

---

## 1. Audit Schema Tables & Utilization

### 1.1 `audit.pipeline_execution_logs`
Stores execution batch metadata, file checksums, duration, and record counters for every file processed.

### 1.2 `audit.data_quality_audit_logs`
Stores granular results of data contract validation assertions (Pydantic / Great Expectations) for every entity chunk.

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `log_id` | `BIGSERIAL` | Primary Key |
| `batch_id` | `VARCHAR(64)` | FK linking to `pipeline_execution_logs` |
| `table_name` | `VARCHAR(100)` | Target entity table (e.g., `orders`) |
| `rule_name` | `VARCHAR(100)` | Validation assertion rule (e.g., `check_non_null_customer_id`) |
| `records_evaluated` | `INT` | Total rows evaluated by the rule |
| `records_passed` | `INT` | Total rows satisfying the rule |
| `records_failed` | `INT` | Total rows violating the rule |
| `executed_at` | `TIMESTAMPTZ` | Timestamp when validation executed |

### 1.3 `audit.quarantine_records`
Stores raw contract-violating records trapped by validation gates, preserving full payload data for triage and replay.

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `quarantine_id` | `BIGSERIAL` | Primary Key |
| `batch_id` | `VARCHAR(64)` | Ingestion batch UUID |
| `source_file` | `VARCHAR(255)` | Source file path |
| `entity_name` | `VARCHAR(100)` | Entity name (e.g., `orders`) |
| `failed_rule` | `VARCHAR(100)` | Assertion rule violated |
| `raw_record_json` | `JSONB` | Complete raw JSON payload of defective record |
| `quarantined_at` | `TIMESTAMPTZ` | Isolation timestamp |

---

## 2. Observability Metrics & Monitoring Dashboard Queries

### Metric 1: Overall Ingestion Pass vs Rejection Rate
```sql
SELECT 
    pipeline_name,
    COUNT(DISTINCT batch_id) AS total_batches,
    SUM(records_discovered) AS total_discovered,
    SUM(records_processed) AS total_processed,
    SUM(records_quarantined) AS total_quarantined,
    ROUND((SUM(records_processed)::NUMERIC / NULLIF(SUM(records_discovered), 0)) * 100, 2) AS pass_rate_pct
FROM audit.pipeline_execution_logs
GROUP BY pipeline_name;
```

### Metric 2: Quarantine Defect Distribution by Violation Rule
```sql
SELECT 
    failed_rule,
    entity_name,
    COUNT(*) AS defect_count
FROM audit.quarantine_records
GROUP BY failed_rule, entity_name
ORDER BY defect_count DESC;
```
