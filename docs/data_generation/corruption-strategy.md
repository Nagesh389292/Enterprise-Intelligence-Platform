# Controlled Data Quality Corruption Strategy
### NexaCore Enterprise Intelligence Platform

---

## 📌 Architectural Purpose

To test the **Data Quality & Observability Layer** (Great Expectations, custom validation gates, quarantine storage), `enterprise_data_generator` incorporates a **Controlled Data Corruption Engine (`corruption/`)**.

```text
               CLEAN DATA GENERATION ENGINE
                            │
                            ▼
               ┌─────────────────────────┐
               │ Data Quality Corruptor  │ (Configurable rate: e.g. 5%)
               └────────────┬────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
     Clean Output Dataset       Corrupted Output Dataset
     (Passed to PySpark ETL)    (Triggers Quarantine Assertions)
```

---

## 1. Supported Corruption Injection Types

| Corruption Category | Target Field | Injected Defect | Pipeline Assertion Tested |
| :--- | :--- | :--- | :--- |
| **Null Injection** | `customer_id`, `order_timestamp` | Replaces valid values with `NULL` or empty strings | Non-Null Constraint Check |
| **Duplicate Keys** | `order_id`, `sku` | Duplicates existing primary/unique key values | Primary Key / Unique Constraint |
| **Orphaned Foreign Keys** | `customer_id` in `orders` | Generates random non-existent UUIDs | Foreign Key Referential Integrity |
| **Negative Metrics** | `quantity`, `unit_price` | Injects negative values (e.g., `quantity = -5`) | Range Check (`CHECK (quantity > 0)`) |
| **Malformed Dates** | `order_timestamp` | Injects invalid strings (`"2026-02-31"`, `"INVALID_DATE"`) | ISO 8601 Timestamp Format Validation |
| **Extreme Outliers** | `temperature_c` | Injects physically impossible values (`+999.9°C`) | Boundary Check |
| **Schema Drift** | Dynamic Columns | Appends unexpected new fields or drops expected fields | Schema Contract Enforcement |
| **Late-Arriving Data** | `recorded_at` | Injects events backdated by 30+ days | Time Window Watermarking / Late Data Handling |

---

## 2. Configuration & Isolation Guarantees

* **Configurable Corruption Rate**: The corruption probability is controlled via CLI (`--corrupt-rate 0.05` for 5% defective records).
* **Strict Separation**: Clean generation output is generated first; corruption transforms are applied as a post-processing pass over a deterministic subset of records.
* **Audit Tagging**: In corrupted datasets, raw records retain an internal metadata flag (`_injected_corruption_type`) to verify whether quarantine assertion gates correctly detect every injected error.
