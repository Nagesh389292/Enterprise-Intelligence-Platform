# Idempotency & Deduplication Architecture
### NexaCore Enterprise Intelligence Platform

---

## 📌 Definition of Idempotency

In data engineering, an ingestion pipeline is **idempotent** if executing it $N$ times over identical input data produces **bit-for-bit identical storage state** in the target database without creating duplicate records or inflating metric aggregates.

$$\text{Pipeline}(\text{Dataset}) = \text{Pipeline}(\text{Pipeline}(\text{Dataset}))$$

---

## 1. Deduplication & Deterministic Record Hashing

To identify duplicate business records across incremental batches, the pipeline computes a **Deterministic Record Hash (`record_hash`)** for every incoming row.

### Record Hash Formula
The hash is calculated using SHA256 over concatenated natural business keys:

$$\text{record\_hash} = \text{SHA256}(\text{NaturalKey}_1 \parallel \text{NaturalKey}_2 \parallel \dots \parallel \text{VersionTimestamp})$$

* **Orders Table**: `SHA256(order_number)`
* **OrderItems Table**: `SHA256(order_id || ":" || product_id)`
* **Inventory Table**: `SHA256(warehouse_id || ":" || product_id || ":" || last_count_date)`
* **Telemetry Table**: `SHA256(machine_id || ":" || recorded_at)`

---

## 2. PostgreSQL Atomic UPSERT Semantics

In the Silver layer (`source.*` tables), primary key tables enforce unique constraints on natural keys or `record_hash`. Ingestion uses PostgreSQL `ON CONFLICT` semantics:

```sql
-- Idempotent UPSERT into source.orders
INSERT INTO source.orders (
    order_id, order_number, customer_id, channel_id, shipping_address_id,
    order_status, order_timestamp, promised_delivery_date, total_amount,
    _ingestion_batch_id, _source_file, _ingested_at
)
VALUES (
    :order_id, :order_number, :customer_id, :channel_id, :shipping_address_id,
    :order_status, :order_timestamp, :promised_delivery_date, :total_amount,
    :batch_id, :source_file, NOW()
)
ON CONFLICT (order_number) 
DO UPDATE SET
    order_status = EXCLUDED.order_status,
    total_amount = EXCLUDED.total_amount,
    _ingestion_batch_id = EXCLUDED._ingestion_batch_id,
    _source_file = EXCLUDED._source_file,
    _ingested_at = NOW()
WHERE source.orders.order_status IS DISTINCT FROM EXCLUDED.order_status;
```

---

## 3. Transactional Batch Isolation

To prevent partial writes from polluting the database:
1. Every file batch runs within an **Explicit Database Transaction Block** (`BEGIN ... COMMIT`).
2. If any unrecoverable error occurs during parsing or database insert, the transaction triggers a **`ROLLBACK`**.
3. No partial records remain in `source.*` schemas; audit logs record the `FAILED` batch status.
