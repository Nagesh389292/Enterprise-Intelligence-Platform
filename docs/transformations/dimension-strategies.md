# Dimension Strategies & Slowly Changing Dimensions (SCD)
### NexaCore Enterprise Intelligence Platform

---

## 📌 Dimension Classification & SCD Matrix

| Dimension Table | SCD Strategy | Tracked Historical Attributes | Rationale |
| :--- | :--- | :--- | :--- |
| `dim_date` | **Static / System Generated** | None (Calendar Reference) | Static reference dataset pre-populated for 2025–2030 |
| `dim_customer` | **SCD Type 2** | `industry`, `segment_name`, `credit_limit`, `primary_city` | Crucial for historical RFM churn modeling and cohort analytics |
| `dim_product` | **SCD Type 1** | None (Overwrite Latest) | Price changes tracked directly via transaction-time `unit_price` in `fact_order_items` |
| `dim_supplier` | **SCD Type 1** | None (Overwrite Latest) | Supplier contact details updated in-place |
| `dim_warehouse` | **SCD Type 1** | None (Overwrite Latest) | Physical warehouse facility attributes rarely change |
| `dim_machine` | **SCD Type 2** | `status`, `warehouse_name` | Relocation or status shifts affect predictive failure models |

---

## 1. SCD Type 2 Architecture & Change Detection

For SCD Type 2 tables (`dim_customer`, `dim_machine`), historical changes create a new version row:

```sql
-- Schema Template for SCD Type 2 Dimensions
CREATE TABLE analytics.dim_customer (
    customer_key BIGSERIAL PRIMARY KEY,
    customer_id UUID NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    industry VARCHAR(100) NOT NULL,
    segment_name VARCHAR(100) NOT NULL,
    credit_limit NUMERIC(12,2) NOT NULL,
    primary_city VARCHAR(100),
    primary_country CHAR(2),
    
    -- SCD Type 2 Tracking Metadata
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    record_version INT NOT NULL DEFAULT 1,
    checksum VARCHAR(64) NOT NULL
);
```

### Change Detection Algorithm
```sql
-- Detect changes using SHA256 hashing over monitored columns
SELECT 
    customer_id,
    SHA256(CONCAT(industry, '|', segment_name, '|', credit_limit, '|', primary_city)) AS current_hash
FROM source.customers;
```

---

## 2. Date Dimension (`dim_date`) Generation Logic

`dim_date` is a pre-generated static table covering 2025-01-01 through 2030-12-31:

```sql
-- Date Dimension Population Query
INSERT INTO analytics.dim_date (
    date_key, full_date, year, quarter, quarter_name, month, month_name,
    week_of_year, day_of_month, day_of_week, day_name, is_weekend
)
SELECT 
    TO_CHAR(d, 'YYYYMMDD')::INT AS date_key,
    d::DATE AS full_date,
    EXTRACT(YEAR FROM d)::INT AS year,
    EXTRACT(QUARTER FROM d)::INT AS quarter,
    'Q' || EXTRACT(QUARTER FROM d)::TEXT AS quarter_name,
    EXTRACT(MONTH FROM d)::INT AS month,
    TO_CHAR(d, 'Month') AS month_name,
    EXTRACT(WEEK FROM d)::INT AS week_of_year,
    EXTRACT(DAY FROM d)::INT AS day_of_month,
    EXTRACT(ISODOW FROM d)::INT AS day_of_week,
    TO_CHAR(d, 'Day') AS day_name,
    CASE WHEN EXTRACT(ISODOW FROM d) IN (6, 7) THEN TRUE ELSE FALSE END AS is_weekend
FROM GENERATE_SERIES('2025-01-01'::DATE, '2030-12-31'::DATE, '1 day'::INTERVAL) d;
```
