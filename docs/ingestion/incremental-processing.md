# Incremental Data Processing & File Discovery Architecture
### NexaCore Enterprise Intelligence Platform

---

## 📌 Executive Overview

To avoid scanning and re-ingesting static historical files on every execution, the ingestion pipeline utilizes a stateful **Incremental File Discovery Engine**.

The engine determines:
1. Which raw files in `data/raw/generated/` are new or modified.
2. Which files have already been processed.
3. What batch ID is currently executing.
4. Whether a failed batch can be safely retried without re-processing completed chunks.

---

## 1. Incremental File Discovery Algorithm

```text
                        START INGESTION RUN
                                │
                                ▼
               Scan `data/raw/generated/*.parquet`
                                │
                                ▼
             For each file, compute MD5 Checksum
                                │
                                ▼
            Query `audit.pipeline_execution_logs`
            WHERE source_file_name = file.name
              AND file_checksum = file.md5
              AND status = 'COMPLETED'
                                │
                 ┌──────────────┴──────────────┐
                 │                             │
           Match Found                   No Match Found
           (File Processed)              (New / Modified File)
                 │                             │
                 ▼                             ▼
            SKIP FILE                    ENQUEUE FILE FOR BATCH
                                               │
                                               ▼
                                      Assign `_ingestion_batch_id`
                                      Execute Ingestion Transaction
                                               │
                                               ▼
                                      Log Completion in Audit DB
```

---

## 2. Checkpoint State Schema

File execution states are recorded in `audit.pipeline_execution_logs`:

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `log_id` | `BIGSERIAL` | Primary Key auto-increment integer |
| `batch_id` | `VARCHAR(64)` | Unique execution UUID (`batch_YYYYMMDD_HHMMSS_XXXX`) |
| `pipeline_name` | `VARCHAR(100)` | Ingestion job identifier (e.g., `ingest_orders_parquet`) |
| `source_file_name` | `VARCHAR(255)` | Relative file path (`data/raw/generated/orders.parquet`) |
| `file_checksum` | `VARCHAR(64)` | MD5 hash of raw file content |
| `file_size_bytes` | `BIGINT` | Raw file size in bytes |
| `records_discovered` | `INT` | Total row count extracted from raw file |
| `records_processed` | `INT` | Total rows successfully inserted into Silver |
| `records_quarantined`| `INT` | Total rows routed to quarantine due to validation errors |
| `status` | `VARCHAR(20)` | Execution status: `STARTED`, `IN_PROGRESS`, `COMPLETED`, `FAILED` |
| `started_at` | `TIMESTAMPTZ` | Timestamp when file ingestion initiated |
| `completed_at` | `TIMESTAMPTZ` | Timestamp when file ingestion finished |
| `error_message` | `TEXT` | Failure error message and stack trace if status is `FAILED` |

---

## 3. Safe Replay & Retry Mechanics

If a pipeline run crashes mid-batch:
* Completed files within the batch retain `status = 'COMPLETED'` and will be skipped on subsequent runs.
* Partially processed files retain `status = 'FAILED'`.
* The retry engine identifies `FAILED` files, executes an atomic cleanup pass (deleting transient records tagged with that file's batch ID), and re-ingests the file cleanly.
