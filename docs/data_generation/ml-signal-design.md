# Machine Learning Causal Signal Design
### NexaCore Enterprise Intelligence Platform

---

## 📌 Executive Overview

To ensure the platform's Machine Learning models learn realistic business logic rather than synthetic noise or artificial target leakage, `enterprise_data_generator` injects **explicit causal signals** into the data graph.

```text
              INJECTED CAUSAL BUSINESS SIGNALS
   ┌─────────────────────────────────────────────────────┐
   │ 1. Customer Churn: Recency Decay + Low CSAT         │
   │ 2. Demand Forecast: Q4 Seasonality + Trend          │
   │ 3. Stockout Risk: High Sales + Supplier Lead Delay  │
   │ 4. IoT Anomaly: Temperature Creep + Vibration Spike │
   │ 5. Machine Failure: Unresolved Anomaly + Wear Age   │
   └─────────────────────────────────────────────────────┘
```

---

## 1. Feature & Target Mappings per Use Case

### 1.1 Customer Churn Prediction (Classification)
* **Target Label**: `is_churned` (1 if account had 0 orders in rolling 90 days, else 0).
* **Injected Causal Signal**: Accounts experiencing repeated delivery delays (`is_delayed`), low CSAT scores ($< 2.5$), and increasing support ticket velocity demonstrate decaying order frequency over a 60-day window.
* **Feature Lineage**: `days_since_last_order`, `order_frequency_30d`, `support_ticket_count_60d`, `avg_csat_score`, `total_lifetime_spend`.
* **Leakage Prevention**: Features are computed strictly using historical data prior to the prediction timestamp cutoff.

### 1.2 Product Demand Forecasting (Time-Series Regression)
* **Target Label**: `daily_unit_sales` per SKU per warehouse over a forward 30-day horizon.
* **Injected Causal Signal**: Incorporates multiplicative seasonal trend curves (Q4 holiday surge, summer lull) combined with promotional discount multipliers.
* **Feature Lineage**: `rolling_7d_unit_sales`, `rolling_30d_unit_sales`, `month_of_year`, `is_promotional_period`, `category_growth_rate`.

### 1.3 Inventory Stockout Risk (Classification / Early Warning)
* **Target Label**: `will_stockout_7d` (1 if `quantity_available` reaches 0 in next 7 days).
* **Injected Causal Signal**: Rapid sales velocity spikes combined with long supplier lead times (`lead_time_days > 21`) deplete warehouse stock faster than reorder replenishment.
* **Feature Lineage**: `current_quantity_available`, `reorder_point`, `sales_velocity_7d`, `supplier_lead_time_days`, `days_of_supply_on_hand`.

### 1.4 IoT Machine Telemetry Anomaly Detection (Unsupervised)
* **Target Label**: `is_anomalous_reading` (Unsupervised isolation / threshold flag).
* **Injected Causal Signal**: 48 hours prior to equipment breakdown, sensor readings exhibit abnormal joint distributions (e.g., high vibration RMS accompanied by rapid hydraulic pressure drops).
* **Feature Lineage**: `temperature_c`, `vibration_rms`, `pressure_psi`, `power_kw`, `temp_vibration_interaction`.

### 1.5 Predictive Equipment Failure (Survival Analysis / Binary Classification)
* **Target Label**: `machine_failed_24h` (1 if failure event occurs in next 24 hours).
* **Injected Causal Signal**: Cumulative machine operating hours, operating temperature exceeding safe max threshold ($> 120^\circ\text{C}$), and time elapsed since last preventive maintenance.
* **Feature Lineage**: `operating_hours_since_maintenance`, `max_temp_last_24h`, `vibration_rms_p95_last_24h`, `machine_age_days`, `historical_failure_count`.
