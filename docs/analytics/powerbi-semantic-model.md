# Enterprise Power BI Semantic Model Architecture Specification

## 1. Architecture Overview & Design Principles

The NexaCore Data Platform enterprise semantic layer is structured as a unified **Multi-Fact Star Schema** designed for Power BI deployment. It translates clean Gold layer tables (`analytics.*`) into a high-performance, single-version-of-truth analytical model for executive decision-making, financial reconciliation, supply chain management, plant operations monitoring, and customer experience tracking.

```
                        ┌───────────────────┐
                        │     dim_date      │
                        └─────────┬─────────┘
                                  │ (1:*)
      ┌───────────────────────────┼───────────────────────────┐
      │                           │                           │
┌─────┴───────────────┐ ┌─────────┴───────────────┐ ┌─────────┴───────────────┐
│     dim_customer    │ │       fact_orders       │ │      dim_warehouse      │
└─────────┬───────────┘ └─────────┬───────────────┘ └─────────┬───────────────┘
          │ (1:*)                 │ (1:*)                     │ (1:*)
          │                       │                           │
          │             ┌─────────┴───────────────┐           │
          └────────────►│    fact_order_items     │◄──────────┘
                        └─────────┬───────────────┘
                                  │ (*:1)
                        ┌─────────┴───────────────┐
                        │       dim_product       │
                        └─────────┬───────────────┘
                                  │ (1:*)
                        ┌─────────┴───────────────┐
                        │ fact_inventory_snapshot │
                        └─────────────────────────┘
```

### Key Architectural Principles
1. **Star Schema Pureness**: Avoid snowflake normalized paths where possible. Dimensional attributes are denormalized into flat dimensions (`dim_customer`, `dim_product`, `dim_warehouse`, `dim_supplier`, `dim_machine`).
2. **Single-Direction Filter Propagation**: All relationships maintain strictly `1:*` cardinality with single-direction filtering (`Dimension -> Fact`). Cross-filtering (`Bi-directional`) is explicitly prohibited to prevent ambiguous filter contexts, fan traps, and incorrect aggregation totals.
3. **Fact-to-Fact Isolation**: Fact tables NEVER connect directly to other fact tables. Inter-fact analytics (e.g., comparing order volume against machine telemetry or support tickets) are executed via shared conformed dimensions (`dim_date`, `dim_customer`, `dim_machine`).
4. **Surrogate Key Integrity**: Integer/string primary keys guarantee zero-orphan lookup resolution across all facts.

---

## 2. Table Classification & Grain Specification

### Conformed Dimensions

| Table Name | Grain / Primary Key | Record Count | Description | Conformed Across |
| :--- | :--- | :--- | :--- | :--- |
| `dim_customer` | `customer_id` (UUID) | 1,000 | Core customer demographic and geographic snapshot. | `fact_orders`, `fact_support_tickets` |
| `dim_product` | `product_id` (UUID) | 100 | Product catalog containing categories, unit costs, and list prices. | `fact_order_items`, `fact_inventory_snapshot` |
| `dim_supplier` | `supplier_id` (UUID) | 25 | Equipment and component supplier metadata. | Operational reporting |
| `dim_warehouse` | `warehouse_id` (UUID) | 5 | Physical distribution center details and regional locations. | `fact_inventory_snapshot` |
| `dim_machine` | `machine_id` (UUID) | 50 | Manufacturing plant equipment asset metadata. | `fact_machine_telemetry`, `fact_maintenance_events` |
| `dim_date` | `date_key` (DATE `YYYY-MM-DD`) | 1,095 | Continuous date dimension (2024-01-01 to 2026-12-31). | **ALL Facts** |

### Fact Tables

| Fact Table Name | Primary Grain | Total Rows | Control Total Metric | Storage Strategy |
| :--- | :--- | :--- | :--- | :--- |
| `fact_orders` | 1 row per Header Order (`order_id`) | 10,000 | Net Revenue: **$18,274,577.78** | Import Mode |
| `fact_order_items` | 1 row per Line Item (`order_item_id`) | 35,193 | Gross Revenue: **$19,330,862.00**, Units: **193,309** | Import Mode / Incremental |
| `fact_inventory_snapshot` | 1 row per Warehouse + Product Snapshot | 500 | Total On-Hand: **184,520 units** | Import Mode |
| `fact_machine_telemetry` | 1 row per 1-minute Machine Aggregation | 100,000 | Total Events: **100,000**, Fleet Size: **50** | Dual / DirectQuery |
| `fact_maintenance_events` | 1 row per Maintenance Log | 10 | Total Downtime: **180 hours** | Import Mode |
| `fact_support_tickets` | 1 row per Customer Ticket | 2,500 | Total Tickets: **2,500**, Avg CSAT: **4.15** | Import Mode |

---

## 3. Relationship Matrix & Filter Propagation Rules

| Primary Table (1) | Foreign Table (*) | Primary Key | Foreign Key | Active State | Filter Direction | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `dim_date` | `fact_orders` | `date_key` | `order_date` | **Active** | Single (`dim_date` -> `fact_orders`) | Drives primary sales revenue timeline |
| `dim_date` | `fact_orders` | `date_key` | `promised_delivery_date` | *Inactive* | Single | Used with `USERELATIONSHIP()` for SLA tracking |
| `dim_customer` | `fact_orders` | `customer_id` | `customer_id` | **Active** | Single (`dim_customer` -> `fact_orders`) | Customer sales breakdown |
| `fact_orders` | `fact_order_items` | `order_id` | `order_id` | **Active** | Single (`fact_orders` -> `fact_order_items`) | Order header to line item relationship |
| `dim_product` | `fact_order_items` | `product_id` | `product_id` | **Active** | Single (`dim_product` -> `fact_order_items`) | Product sales breakdown |
| `dim_warehouse` | `fact_inventory_snapshot` | `warehouse_id` | `warehouse_id` | **Active** | Single (`dim_warehouse` -> `fact_inventory`) | Warehouse stock breakdown |
| `dim_product` | `fact_inventory_snapshot` | `product_id` | `product_id` | **Active** | Single (`dim_product` -> `fact_inventory`) | Product stock breakdown |
| `dim_date` | `fact_inventory_snapshot` | `date_key` | `snapshot_date` | **Active** | Single (`dim_date` -> `fact_inventory`) | Semi-additive stock calculation |
| `dim_machine` | `fact_machine_telemetry` | `machine_id` | `machine_id` | **Active** | Single (`dim_machine` -> `fact_telemetry`) | Sensor telemetry lookup |
| `dim_date` | `fact_machine_telemetry` | `date_key` | `telemetry_date` | **Active** | Single (`dim_date` -> `fact_telemetry`) | Daily telemetry trends |
| `dim_machine` | `fact_maintenance_events` | `machine_id` | `machine_id` | **Active** | Single (`dim_machine` -> `fact_maintenance`) | Machine maintenance logs |
| `dim_date` | `fact_maintenance_events` | `date_key` | `maintenance_date` | **Active** | Single (`dim_date` -> `fact_maintenance`) | Downtime calendar tracking |
| `dim_customer` | `fact_support_tickets` | `customer_id` | `customer_id` | **Active** | Single (`dim_customer` -> `fact_tickets`) | Support ticket customer lookup |
| `dim_date` | `fact_support_tickets` | `date_key` | `created_date` | **Active** | Single (`dim_date` -> `fact_tickets`) | Support volume calendar tracking |

---

## 4. Date Dimension Configuration

`dim_date` is marked as the official **Date Table** in Power BI.
- **Date Key Column**: `date_key` (DataType: `Date`, Format: `YYYY-MM-DD`).
- **Contiguity**: Continuous sequence with zero missing dates covering 3 years (1,095 days).
- **Time Intelligence Requirements**: All DAX measures utilizing `SAMEPERIODLASTYEAR`, `TOTALYTD`, and `DATEADD` rely explicitly on `dim_date[date_key]`.

---

## 5. Row-Level Security (RLS) Strategy & Role Definitions

RLS is enforced dynamically at the semantic layer using standard DAX filter expressions to comply with enterprise data governance.

### Role Definitions & DAX Expressions

#### 1. `Executive_RLS`
- **Scope**: C-Suite, VPs, and Global Analytics Directors.
- **Access Level**: Full unfiltered visibility across all tables, facts, and metrics.
- **DAX Filter Expression**: None (No filter applied).

#### 2. `Regional_Manager_RLS`
- **Scope**: Regional Sales Directors and Field Managers.
- **Access Level**: Restricted to customer transactions and inventory within assigned geographic regions.
- **DAX Filter Expression on `dim_customer`**:
  ```dax
  [country] = LOOKUPVALUE(
      UserSecurityMapping[AssignedRegion],
      UserSecurityMapping[UserPrincipalName],
      USERPRINCIPALNAME()
  )
  ```
- **DAX Filter Expression on `dim_warehouse`**:
  ```dax
  [region] = LOOKUPVALUE(
      UserSecurityMapping[AssignedRegion],
      UserSecurityMapping[UserPrincipalName],
      USERPRINCIPALNAME()
  )
  ```

#### 3. `Plant_Operations_RLS`
- **Scope**: Plant Engineers and Equipment Reliability Specialists.
- **Access Level**: Restricted to telemetry and maintenance logs for machines located in their specific manufacturing facility.
- **DAX Filter Expression on `dim_machine`** (or `fact_machine_telemetry` via relationship):
  ```dax
  [plant_location] = LOOKUPVALUE(
      UserSecurityMapping[AssignedPlant],
      UserSecurityMapping[UserPrincipalName],
      USERPRINCIPALNAME()
  )
  ```

---

## 6. Performance Optimization & Refresh Strategy

1. **Storage Modes**:
   - `dim_*` tables, `fact_orders`, `fact_order_items`, `fact_inventory_snapshot`, `fact_maintenance_events`, `fact_support_tickets`: **Import Mode** (In-Memory VertiPaq compression for maximum query performance).
   - `fact_machine_telemetry`: **Dual Mode / DirectQuery Aggregations** (Pre-aggregated 1-minute rollups in Import mode, DirectQuery drill-through to raw sensor stream).
2. **Incremental Refresh Policy**:
   - `fact_order_items` & `fact_orders`: Incremental refresh configured with 2-year store history and 14-day detect-data-changes window based on `_ingested_at`.
3. **VertiPaq Engine Column Optimization**:
   - High-cardinality GUID strings (`order_id`, `customer_id`, `product_id`) kept for relationship linkage but hidden from end-user reporting interface.
   - Numeric measures formatted cleanly; floating-point columns rounded to 2 decimal places.
