# Data Lineage & Traceability Architecture
### NexaCore Enterprise Intelligence Platform

---

## 📌 Architectural Purpose

**Data Lineage** guarantees that every data point displayed on an executive Power BI dashboard or consumed by an AI ML model can be traced backwards through every transformation layer to its exact raw source file and ingestion batch.

```text
                               DATA LINEAGE TRAVERSAL MAP
 ┌─────────────────────────────────────────────────────────────────────────────────────────┐
 │ Analytics Gold Fact Record: fact_orders (order_key=8492)                                 │
 └───────────────────────────────────────────▲─────────────────────────────────────────────┘
                                             │ (dbt transformation)
 ┌───────────────────────────────────────────┴─────────────────────────────────────────────┐
 │ Silver Source Record: source.orders (order_number='ORD-2026-010042')                    │
 │ Metadata: _ingestion_batch_id = 'batch_20260817_120000_a1b2', _source_file = 'orders.pq' │
 └───────────────────────────────────────────▲─────────────────────────────────────────────┘
                                             │ (ingestion pipeline execution)
 ┌───────────────────────────────────────────┴─────────────────────────────────────────────┐
 │ Audit Batch Execution Log: audit.pipeline_execution_logs (log_id=142)                   │
 │ Metadata: file_checksum = 'e99a18c4...', started_at = '2026-08-17 12:00:00 UTC'          │
 └───────────────────────────────────────────▲─────────────────────────────────────────────┘
                                             │ (file landing)
 ┌───────────────────────────────────────────┴─────────────────────────────────────────────┐
 │ Raw Source Parquet File: data/raw/generated/orders.parquet                              │
 └─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Lineage Metadata Injection Standard

Every table in `source.*` (Silver layer) and `analytics.*` (Gold layer) includes standard lineage audit columns:

```sql
-- Standard Metadata Lineage Columns
ALTER TABLE source.orders ADD COLUMN _ingestion_batch_id VARCHAR(64) NOT NULL;
ALTER TABLE source.orders ADD COLUMN _source_file VARCHAR(255) NOT NULL;
ALTER TABLE source.orders ADD COLUMN _ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
```

---

## 2. Lineage Audit Trace Queries

### Trace 1: Find Raw File and Batch ID for a Specific Customer Order
```sql
SELECT 
    o.order_number,
    o.order_status,
    o.total_amount,
    o._ingestion_batch_id,
    o._source_file,
    o._ingested_at,
    log.file_checksum,
    log.status AS batch_status
FROM source.orders o
JOIN audit.pipeline_execution_logs log 
  ON o._ingestion_batch_id = log.batch_id
WHERE o.order_number = 'ORD-2026-010042';
```

### Trace 2: List All Silver Tables Ingested by a Single Execution Batch
```sql
SELECT 'orders' AS table_name, COUNT(*) FROM source.orders WHERE _ingestion_batch_id = 'batch_20260817_120000_a1b2'
UNION ALL
SELECT 'order_items', COUNT(*) FROM source.order_items WHERE _ingestion_batch_id = 'batch_20260817_120000_a1b2'
UNION ALL
SELECT 'machine_telemetry', COUNT(*) FROM source.machine_telemetry WHERE _ingestion_batch_id = 'batch_20260817_120000_a1b2';
```
