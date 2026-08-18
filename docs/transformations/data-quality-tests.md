# Gold Layer Data Quality & Assertion Testing
### NexaCore Enterprise Intelligence Platform

---

## 📌 Data Quality Assertions Matrix

Every Gold dimension and fact model includes automated schema and data assertion tests executed during dbt transformations.

| Target Table | Test Category | Assertion Rule | Severity |
| :--- | :--- | :--- | :--- |
| `dim_customer` | **Uniqueness** | `customer_key` is unique | ERROR (Fail Build) |
| `dim_customer` | **Not Null** | `customer_id`, `company_name` non-null | ERROR (Fail Build) |
| `dim_product` | **Range Check** | `unit_price >= unit_cost` | WARNING (Alert Log) |
| `fact_orders` | **Uniqueness** | `order_key` is unique | ERROR (Fail Build) |
| `fact_orders` | **FK Integrity** | `customer_key` exists in `dim_customer` | ERROR (Fail Build) |
| `fact_orders` | **Accepted Values** | `order_status` IN (`PENDING`, `PROCESSING`, `SHIPPED`, `DELIVERED`, `CANCELLED`) | ERROR (Fail Build) |
| `fact_order_items` | **Quantity Bound**| `quantity > 0` | ERROR (Fail Build) |
| `fact_order_items` | **Revenue Bound**| `net_revenue >= 0` | WARNING (Alert Log) |
| `fact_inventory_daily` | **Composite Key**| `(warehouse_key, product_key, snapshot_date)` is unique | ERROR (Fail Build) |
| `fact_machine_telemetry`| **Range Check** | `avg_temperature_c` BETWEEN -50 AND 300 | ERROR (Fail Build) |

---

## 1. Custom Singular Test SQL Examples

### Test 1: Orphan Customer Foreign Keys in `fact_orders`
```sql
-- tests/assert_no_orphan_customers_in_fact_orders.sql
SELECT 
    f.order_number,
    f.customer_key
FROM {{ ref('fact_orders') }} f
LEFT JOIN {{ ref('dim_customer') }} d ON f.customer_key = d.customer_key
WHERE d.customer_key IS NULL;
```

### Test 2: Net Revenue Reconciliation Test
```sql
-- tests/assert_order_item_revenue_matches_order_total.sql
WITH item_sums AS (
    SELECT order_key, SUM(net_revenue) AS calculated_total
    FROM {{ ref('fact_order_items') }}
    GROUP BY order_key
)
SELECT 
    o.order_number,
    o.total_amount,
    i.calculated_total,
    ABS(o.total_amount - i.calculated_total) AS diff
FROM {{ ref('fact_orders') }} o
JOIN item_sums i ON o.order_key = i.order_key
WHERE ABS(o.total_amount - i.calculated_total) > 0.05;
```
