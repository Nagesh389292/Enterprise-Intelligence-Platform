# NexaCore Data Ingestion Framework
### Enterprise Intelligence Platform

---

## 📌 Executive Summary

The **NexaCore Data Ingestion Framework** is a production-grade, fault-tolerant ingestion architecture designed to move raw multi-domain enterprise data (Parquet / CSV files in `data/raw/generated/`) into the enterprise data warehouse and lakehouse layers.

It implements a **Medallion Architecture (Raw $\rightarrow$ Bronze $\rightarrow$ Silver $\rightarrow$ Gold)** with **incremental file discovery**, **atomic idempotency**, **data quality quarantine routing**, and **audit log tracking**.

---

## 📂 Documentation Sitemap

* [`ingestion-architecture.md`](file:///c:/Users/NAGESH%20REDDY/Desktop/Data%20Analytics/enterprise-intelligence-platform/docs/ingestion/ingestion-architecture.md) — Medallion layer boundaries, storage formats, and component responsibilities.
* [`incremental-processing.md`](file:///c:/Users/NAGESH%20REDDY/Desktop/Data%20Analytics/enterprise-intelligence-platform/docs/ingestion/incremental-processing.md) — File discovery algorithms, MD5 checksum tracking, watermark state checkpoints.
* [`idempotency.md`](file:///c:/Users/NAGESH%20REDDY/Desktop/Data%20Analytics/enterprise-intelligence-platform/docs/ingestion/idempotency.md) — Deterministic record hashing, UPSERT semantics, and atomic transaction design.
* [`data-lineage.md`](file:///c:/Users/NAGESH%20REDDY/Desktop/Data%20Analytics/enterprise-intelligence-platform/docs/ingestion/data-lineage.md) — Lineage tracking metadata (`_ingestion_batch_id`, `_source_file`, `_ingested_at`).
* [`observability.md`](file:///c:/Users/NAGESH%20REDDY/Desktop/Data%20Analytics/enterprise-intelligence-platform/docs/ingestion/observability.md) — Pipeline execution logs, metric telemetry, and quarantine monitoring (`audit` schema).
* [`error-handling.md`](file:///c:/Users/NAGESH%20REDDY/Desktop/Data%20Analytics/enterprise-intelligence-platform/docs/ingestion/error-handling.md) — Retry policies, exponential backoff, dead-letter quarantine, and disaster recovery.

---

## 🛠️ Planned CLI Specification (Stage 3B Target)

```bash
# Execute incremental batch ingestion for all newly arrived raw files
python -m ingestion.cli run --mode incremental --batch-size 5000

# Execute full backfill re-ingestion with data quality validation
python -m ingestion.cli run --mode full --validate --quarantine-on-error

# Replay failed ingestion batch by batch ID
python -m ingestion.cli replay --batch-id "batch_20260817_120000_a1b2"
```
