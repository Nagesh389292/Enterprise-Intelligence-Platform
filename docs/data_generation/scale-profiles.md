# Dataset Scale Profiles & Benchmarking Specifications
### NexaCore Enterprise Intelligence Platform

---

## 📌 Scale Profile Comparison Matrix

The `enterprise_data_generator` supports three explicit dataset sizing profiles configured via YAML settings (`config/profiles.py`):

| Metric / Entity | `development` Profile | `integration` Profile | `scale` Profile (Benchmark) |
| :--- | :--- | :--- | :--- |
| **Customers** | 1,000 | 10,000 | 100,000 |
| **Customer Addresses** | 1,500 | 15,000 | 150,000 |
| **Product SKUs** | 100 | 1,000 | 5,000 |
| **Suppliers** | 20 | 100 | 500 |
| **Warehouses** | 4 | 8 | 12 |
| **Orders** | 10,000 | 250,000 | 2,000,000 |
| **Order Items** | 35,000 | 875,000 | 7,000,000 |
| **Daily Inventory Records**| 36,500 | 730,000 | 5,475,000 |
| **Machines** | 50 | 100 | 500 |
| **IoT Telemetry Signals** | 100,000 | 1,000,000 | 20,000,000 |
| **Support Tickets** | 2,500 | 50,000 | 400,000 |

---

## 1. Storage & Memory Volume Estimates

```text
                  ESTIMATED STORAGE DISK FOOTPRINT
   ┌─────────────────────────────────────────────────────────────┐
   │ • Development Profile:   ~50 MB CSV / ~15 MB Parquet        │
   │ • Integration Profile:   ~1.2 GB CSV / ~350 MB Parquet      │
   │ • Scale Profile:         ~15.0 GB CSV / ~4.2 GB Parquet     │
   └─────────────────────────────────────────────────────────────┘
```

---

## 2. Usage Intent per Profile

1. **`development` Profile**:
   * Designed for fast local iteration, unit test execution, and schema validation.
   * Runs in sub-10 seconds on local developer machines.
2. **`integration` Profile**:
   * Designed for dbt transformation testing, PySpark Bronze-to-Silver ETL pipeline validation, and local ML model training.
3. **`scale` Profile**:
   * Designed for distributed processing performance benchmarking, PySpark partition tuning, data lake Parquet compaction tests, and load testing FastAPI serving endpoints.
