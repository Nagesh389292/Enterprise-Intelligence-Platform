# NexaCore Data Transformation Framework
### Enterprise Intelligence Platform

---

## 📌 Executive Summary

The **NexaCore Data Transformation Framework** defines the architectural specification for converting Silver conformed data (`source.*` schema) into Gold analytical star-schema models (`analytics.*` schema) in the enterprise data warehouse.

It establishes a 3-tier **dbt Core (Data Build Tool)** modeling architecture combined with **PySpark** distributed processing for high-frequency time-series telemetry.

---

## 📂 Documentation Sitemap

* [`transformation-architecture.md`](file:///c:/Users/NAGESH%20REDDY/Desktop/Data%20Analytics/enterprise-intelligence-platform/docs/transformations/transformation-architecture.md) — Architectural blueprint, dbt model layers (`staging` $\rightarrow$ `intermediate` $\rightarrow$ `marts`), and PySpark integration.
* [`dimensional-model.md`](file:///c:/Users/NAGESH%20REDDY/Desktop/Data%20Analytics/enterprise-intelligence-platform/docs/transformations/dimensional-model.md) — Star schema specification for 6 Dimensions and 6 Facts.
* [`fact-grains.md`](file:///c:/Users/NAGESH%20REDDY/Desktop/Data%20Analytics/enterprise-intelligence-platform/docs/transformations/fact-grains.md) — Detailed grain specifications, natural/surrogate key logic, and derived metrics.
* [`dimension-strategies.md`](file:///c:/Users/NAGESH%20REDDY/Desktop/Data%20Analytics/enterprise-intelligence-platform/docs/transformations/dimension-strategies.md) — Slowly Changing Dimension (SCD Type 1 vs Type 2) strategies and `dim_date` generator.
* [`incremental-transformations.md`](file:///c:/Users/NAGESH%20REDDY/Desktop/Data%20Analytics/enterprise-intelligence-platform/docs/transformations/incremental-transformations.md) — Incremental dbt refresh mechanics (`is_incremental()`) and MERGE semantics.
* [`data-quality-tests.md`](file:///c:/Users/NAGESH%20REDDY/Desktop/Data%20Analytics/enterprise-intelligence-platform/docs/transformations/data-quality-tests.md) — Gold-layer data quality assertions and test specs.
* [`ml-feature-lineage.md`](file:///c:/Users/NAGESH%20REDDY/Desktop/Data%20Analytics/enterprise-intelligence-platform/docs/transformations/ml-feature-lineage.md) — Mapping Gold tables to 5 ML use cases with strict anti-leakage temporal cutoffs.
* [`agent-data-mapping.md`](file:///c:/Users/NAGESH%20REDDY/Desktop/Data%20Analytics/enterprise-intelligence-platform/docs/transformations/agent-data-mapping.md) — Mapping Gold entities and metrics to 9 domain AI agents.

---

## 🏗️ Proposed dbt Project Directory Structure (Stage 4B Target)

```text
dbt/
├── dbt_project.yml
├── profiles.yml
├── models/
│   ├── staging/                  # Clean 1:1 view wrappers over source.* tables
│   │   ├── stg_customers.sql
│   │   ├── stg_orders.sql
│   │   └── stg_products.sql
│   ├── intermediate/             # Business logic, aggregations & joins
│   │   ├── int_customer_rfm.sql
│   │   └── int_order_metrics.sql
│   └── marts/                    # Final Gold Star Schema (analytics.* schema)
│       ├── core/
│       │   ├── dim_customer.sql
│       │   ├── dim_product.sql
│       │   ├── dim_date.sql
│       │   ├── fact_orders.sql
│       │   └── fact_order_items.sql
│       ├── supply_chain/
│       │   ├── dim_supplier.sql
│       │   ├── dim_warehouse.sql
│       │   └── fact_inventory_daily.sql
│       └── operations/
│           ├── dim_machine.sql
│           ├── fact_machine_telemetry.sql
│           ├── fact_maintenance_events.sql
│           └── fact_support_tickets.sql
├── tests/                        # Custom singular data quality tests
├── macros/                       # Reusable SQL helper macros (e.g. surrogate keys)
├── seeds/                        # Static lookup files (e.g. holiday calendar)
└── snapshots/                    # dbt snapshots for SCD Type 2 dimension tracking
```
