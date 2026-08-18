# Enterprise Data Generation Engine (`enterprise_data_generator`)
### NexaCore Enterprise Intelligence Platform

---

## 📌 Executive Summary

The **Enterprise Data Generation Engine (`enterprise_data_generator`)** is a modular Python package designed to simulate the data-producing systems of NexaCore Industries. 

Rather than generating independent random numbers, `enterprise_data_generator` models a multi-domain relational graph connecting **Customers, Products, Sales, Supply Chain, Operations/IoT, and Support**. It injects realistic temporal trends, causal business behaviors, machine learning signals, and controllable data quality corruption.

---

## 📂 Documentation Sitemap

* [`generator-architecture.md`](file:///c:/Users/NAGESH%20REDDY/Desktop/Data%20Analytics/enterprise-intelligence-platform/docs/data_generation/generator-architecture.md) — Technical module design, package structure, seed-based reproducibility, and writer interfaces.
* [`generation-rules.md`](file:///c:/Users/NAGESH%20REDDY/Desktop/Data%20Analytics/enterprise-intelligence-platform/docs/data_generation/generation-rules.md) — Entity dependency DAG, domain generation rules, and business behavior algorithms.
* [`ml-signal-design.md`](file:///c:/Users/NAGESH%20REDDY/Desktop/Data%20Analytics/enterprise-intelligence-platform/docs/data_generation/ml-signal-design.md) — Injected causal signals for Churn, Demand Forecasting, Inventory Stockouts, Anomaly Detection, and Equipment Failure.
* [`corruption-strategy.md`](file:///c:/Users/NAGESH%20REDDY/Desktop/Data%20Analytics/enterprise-intelligence-platform/docs/data_generation/corruption-strategy.md) — Configurable data quality corruption layer for pipeline quarantine testing.
* [`scale-profiles.md`](file:///c:/Users/NAGESH%20REDDY/Desktop/Data%20Analytics/enterprise-intelligence-platform/docs/data_generation/scale-profiles.md) — Detailed dataset scale profiles (`dev`, `integration`, `scale`).

---

## 🛠️ CLI Interface Specification

The engine is invoked via a CLI module:

```bash
# Generate development dataset to CSV
python -m enterprise_data_generator.cli generate --profile dev --format csv --output-dir ./data/raw

# Generate integration dataset with 5% data quality corruption
python -m enterprise_data_generator.cli generate --profile integration --corrupt-rate 0.05 --seed 42

# Direct database insertion mode (Future Stage)
python -m enterprise_data_generator.cli stream --target-db postgres --rate 100
```
