# Entity Generation Dependency & Business Behavior Rules
### NexaCore Enterprise Intelligence Platform

---

## 1. Entity Generation Dependency Graph (DAG)

Entities must be generated strictly in topological order to preserve referential integrity:

```text
  Level 0 (Base Master Dimensions)
  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
  │customer_segments │  │product_categories│  │    suppliers     │  │  machine_types   │
  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
           │                     │                     │                     │
  Level 1  ▼                     ▼                     │                     │
  ┌──────────────────┐  ┌──────────────────┐           │                     │
  │    customers     │  │     products     │◄──────────┘                     │
  └────────┬─────────┘  └────────┬─────────┘                                 │
           │                     │                                           │
  Level 2  ▼                     │    ┌──────────────────┐                   │
  ┌──────────────────┐           │    │    warehouses    │                   │
  │customer_addresses│           │    └────────┬─────────┘                   │
  └────────┬─────────┘           │             │                             │
           │                     │             │                             │
  Level 3  ▼                     ▼             ▼                             ▼
  ┌──────────────────────────────────────────────┐                 ┌──────────────────┐
  │                    orders                    │                 │     machines     │
  └──────────────────────┬───────────────────────┘                 └────────┬─────────┘
                         │                                                  │
  Level 4                ▼                                                  ▼
  ┌──────────────────────────────────────────────┐                 ┌──────────────────┐
  │                  order_items                 │                 │ machine_telemetry│
  └──────────────────────────────────────────────┘                 └────────┬─────────┘
                         │                                                  │
  Level 5                ▼                                                  ▼
  ┌──────────────────────┬───────────────────────┐                 ┌──────────────────┐
  │  support_tickets     │ inventory_transactions│                 │ failure_events   │
  └────────┬─────────────┘ └─────────────────────┘                 └────────┬─────────┘
           │                                                                │
  Level 6  ▼                                                                ▼
  ┌──────────────────────┐                                         ┌──────────────────┐
  │customer_satisfaction │                                         │maintenance_events│
  └──────────────────────┘                                         └──────────────────┘
```

---

## 2. Business Behavior Algorithms per Domain

### 2.1 Customer Domain Rules
* **Segment Allocation**: Accounts are partitioned: Enterprise (10%), Mid-Market (30%), SMB (60%).
* **Credit Limits**: Scaled by segment (Enterprise: $500K-$2M; Mid-Market: $50K-$250K; SMB: $10K-$50K).
* **Regional Distribution**: Multi-region distribution across North America (35%), Europe (30%), APAC (20%), LatAm (10%), MEA (5%).

### 2.2 Product & Sales Order Rules
* **Pareto Popularity (80/20 Rule)**: 20% of product SKUs generate 80% of order volume.
* **Order Basket Size**: 1 to 8 distinct SKUs per order header; quantities follow a Poisson distribution ($\lambda = 3$).
* **Seasonality Curves**: Sales volume incorporates Q4 holiday spikes (+40% demand in Nov-Dec) and Q1 manufacturing lulls (-20% in Jan-Feb).

### 2.3 Inventory & Replenishment Rules
* **Daily Stock Depletion**: Daily order items decrease physical stock `quantity_on_hand`.
* **Reorder Trigger**: When `quantity_on_hand <= reorder_point`, an inventory receipt transaction is scheduled after supplier lead time.
* **Stockout Occurrence**: High-demand products occasionally trigger stockout events (`quantity_on_hand == 0`) due to supplier lead time variance.

### 2.4 Industrial IoT Telemetry & Degradation Rules
* **Normal Sensor Operational Ranges**:
  * Temperature: $65.0^\circ\text{C} \pm 5.0^\circ\text{C}$
  * Vibration RMS: $1.2 \pm 0.3\text{ mm/s}$
  * Pressure: $90.0 \pm 4.0\text{ PSI}$
  * Power: $45.0 \pm 3.0\text{ kW}$
* **Degradation Pattern Engine**: Machines approaching failure exhibit exponential temperature creep ($+0.5^\circ\text{C}$ per hour) and vibration RMS spikes ($> 4.5\text{ mm/s}$) over a 48-hour pre-failure window.

### 2.5 Support Ticket & CSAT Rules
* **Trigger Mechanics**: Product defects or order delivery delays (`is_delayed == 1`) trigger support tickets.
* **Resolution Cadence**: Urgent tickets resolve within 4-12 hours; Low priority within 48-120 hours.
* **CSAT Rating Distribution**: Correlated with resolution hours and order delays (Delayed orders drop mean CSAT from 4.5 to 2.1).
