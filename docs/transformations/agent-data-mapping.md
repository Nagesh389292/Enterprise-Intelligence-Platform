# TradingAgents Multi-Agent Data Mapping Specification
### NexaCore Enterprise Intelligence Platform

---

## 📌 Multi-Agent Architecture Data Routing Map

The Gold star-schema layer (`analytics.*`) directly feeds domain analysis, predictive modeling, risk evaluation, and decision manager agents in the **TradingAgents Multi-Agent Decision System**.

```text
                               GOLD STAR SCHEMA (`analytics.*`)
 ┌─────────────────┬──────────────────┬──────────────────────┬──────────────────────┐
 │  dim_customer   │   dim_product    │    dim_warehouse     │     dim_machine      │
 │   fact_orders   │ fact_order_items │ fact_inventory_daily │fact_machine_telemetry│
 └────────┬────────┴────────┬─────────┴──────────┬───────────┴──────────┬───────────┘
          │                 │                    │                      │
          ▼                 ▼                    ▼                      ▼
 ┌─────────────────┐┌───────────────┐  ┌──────────────────┐  ┌────────────────────┐
 │Customer Analyst ││ Sales Analyst │  │ Inventory Analyst│  │ Operations Analyst │
 └────────┬────────┘└───────┬───────┘  └─────────┬────────┘  └─────────┬──────────┘
          │                 │                    │                     │
          └─────────────────┴──────────┬─────────┴─────────────────────┘
                                       │
                                       ▼
                         ┌───────────────────────────┐
                         │   ML Prediction Agent     │  (Consumes Churn/Demand/Failure Models)
                         └─────────────┬─────────────┘
                                       │
                                       ▼
                         ┌───────────────────────────┐
                         │   Business Critic Agent   │  (Challenges Recommendations & Margins)
                         └─────────────┬─────────────┘
                                       │
                                       ▼
                         ┌───────────────────────────┐
                         │        Risk Agent         │  (Evaluates Exposure, Lead Time, SLA)
                         └─────────────┬─────────────┘
                                       │
                                       ▼
                         ┌───────────────────────────┐
                         │  Decision Manager Agent   │  (Issues Final Executable Action)
                         └───────────────────────────┘
```

---

## 1. Domain Agent Mapping & Data Consumed

### 1.1 Customer Analyst Agent
* **Role**: Analyzes customer retention, RFM segment shifts, churn risk, and support satisfaction.
* **Consumed Gold Tables**: `dim_customer`, `fact_orders`, `fact_support_tickets`
* **Key Metrics**: Recency days, 90-day order frequency, customer lifetime revenue, average CSAT score, open ticket counts.
* **Agent Reasoning Prompt Context**:
  > *"Customer Acme Corp has experienced a CSAT drop from 4.8 to 2.1 over the past 30 days following 2 shipping delays. Churn probability predicted at 78.4%. Recommend account manager outreach and credit limit hold."*

### 1.2 Sales Analyst Agent
* **Role**: Monitors product revenue performance, discount rates, gross profit margins, and channel performance.
* **Consumed Gold Tables**: `dim_product`, `fact_orders`, `fact_order_items`
* **Key Metrics**: Gross revenue, net revenue, discount percentage, gross profit margin %, delivery delay rates.

### 1.3 Inventory Analyst Agent
* **Role**: Monitors warehouse stock levels, stockout risks, supplier lead times, and reorder triggers.
* **Consumed Gold Tables**: `dim_product`, `dim_warehouse`, `dim_supplier`, `fact_inventory_daily`, `fact_order_items`
* **Key Metrics**: Quantity on hand, quantity allocated, days of supply, reorder threshold flag, supplier lead time days.

### 1.4 Operations Analyst Agent
* **Role**: Tracks industrial machine health, telemetry anomalies, preventive maintenance schedules, and breakdown risks.
* **Consumed Gold Tables**: `dim_machine`, `fact_machine_telemetry`, `fact_maintenance_events`, `fact_failure_events`
* **Key Metrics**: 1-min average/max temperature, 1-min RMS vibration, temperature anomaly flag, downtime hours, days since last maintenance.

### 1.5 Data Quality Agent
* **Role**: Monitors Gold-layer contract test assertions, referential integrity errors, and quarantine record counts.
* **Consumed Audit Tables**: `audit.data_quality_audit_logs`, `audit.quarantine_records`, `audit.pipeline_execution_logs`
* **Key Metrics**: Quarantine rejection rates, assertion pass %, unmapped foreign key counts.

### 1.6 ML Prediction Agent
* **Role**: Integrates quantitative prediction scores (Churn %, Demand Forecast, Stockout Risk %, Failure %) with qualitative agent context.

### 1.7 Business Critic Agent
* **Role**: Challenges domain recommendations against margin impact, working capital, and contractual obligations.

### 1.8 Risk Agent
* **Role**: Evaluates systemic risk exposure (supplier concentration, operational downtime cascades, financial credit exposure).

### 1.9 Decision Manager Agent
* **Role**: Synthesizes all agent inputs and issues the final, unified executive decision (e.g., *"Reorder SKU-4820 immediately from Supplier Alpha; halt Machine M-104 for preventive maintenance"*).
