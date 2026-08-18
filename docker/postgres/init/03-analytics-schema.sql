-- ==============================================================================
-- Enterprise Intelligence Platform — Database Initialization Script 03
-- Description: Creates Gold Layer Dimensional Star Schema Tables under 'analytics' schema
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. DIMENSION TABLES
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS analytics.dim_date (
    date_key INT PRIMARY KEY, -- Formatted as YYYYMMDD
    full_date DATE NOT NULL UNIQUE,
    day_of_week INT NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
    day_name VARCHAR(10) NOT NULL,
    day_of_month INT NOT NULL CHECK (day_of_month BETWEEN 1 AND 31),
    day_of_year INT NOT NULL CHECK (day_of_year BETWEEN 1 AND 366),
    week_of_year INT NOT NULL CHECK (week_of_year BETWEEN 1 AND 53),
    month_number INT NOT NULL CHECK (month_number BETWEEN 1 AND 12),
    month_name VARCHAR(15) NOT NULL,
    quarter INT NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    year INT NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    is_holiday BOOLEAN NOT NULL DEFAULT FALSE
);

-- Customer Dimension (SCD Type 2)
CREATE TABLE IF NOT EXISTS analytics.dim_customer (
    customer_key SERIAL PRIMARY KEY,
    customer_id UUID NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    industry VARCHAR(100) NOT NULL,
    segment_code VARCHAR(30) NOT NULL,
    segment_name VARCHAR(100) NOT NULL,
    account_status VARCHAR(20) NOT NULL,
    contact_email VARCHAR(255) NOT NULL,
    credit_limit NUMERIC(12,2) NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMPTZ,
    is_current BOOLEAN NOT NULL DEFAULT TRUE
);

-- Product Dimension (SCD Type 1)
CREATE TABLE IF NOT EXISTS analytics.dim_product (
    product_key SERIAL PRIMARY KEY,
    product_id UUID NOT NULL UNIQUE,
    sku VARCHAR(50) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    category_name VARCHAR(100) NOT NULL,
    parent_category_name VARCHAR(100),
    unit_cost NUMERIC(10,2) NOT NULL,
    unit_price NUMERIC(10,2) NOT NULL,
    reorder_point INT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Supplier Dimension (SCD Type 1)
CREATE TABLE IF NOT EXISTS analytics.dim_supplier (
    supplier_key SERIAL PRIMARY KEY,
    supplier_id UUID NOT NULL UNIQUE,
    supplier_code VARCHAR(30) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    quality_rating NUMERIC(3,2),
    lead_time_days INT NOT NULL,
    country_code CHAR(2) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Warehouse Dimension (SCD Type 1)
CREATE TABLE IF NOT EXISTS analytics.dim_warehouse (
    warehouse_key SERIAL PRIMARY KEY,
    warehouse_id UUID NOT NULL UNIQUE,
    warehouse_code VARCHAR(30) NOT NULL,
    warehouse_name VARCHAR(100) NOT NULL,
    region VARCHAR(50) NOT NULL,
    capacity_sqft INT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Machine Dimension (SCD Type 2)
CREATE TABLE IF NOT EXISTS analytics.dim_machine (
    machine_key SERIAL PRIMARY KEY,
    machine_id UUID NOT NULL,
    serial_number VARCHAR(100) NOT NULL,
    type_name VARCHAR(100) NOT NULL,
    manufacturer VARCHAR(100) NOT NULL,
    warehouse_code VARCHAR(30) NOT NULL,
    installation_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL,
    max_temperature_c NUMERIC(5,2) NOT NULL,
    max_vibration_rms NUMERIC(5,2) NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMPTZ,
    is_current BOOLEAN NOT NULL DEFAULT TRUE
);

-- ------------------------------------------------------------------------------
-- 2. FACT TABLES
-- ------------------------------------------------------------------------------

-- Grain: 1 record per order header
CREATE TABLE IF NOT EXISTS analytics.fact_orders (
    order_key BIGSERIAL PRIMARY KEY,
    order_id UUID NOT NULL UNIQUE,
    order_number VARCHAR(50) NOT NULL,
    customer_key INT NOT NULL REFERENCES analytics.dim_customer(customer_key),
    channel_id INT NOT NULL,
    shipping_address_id UUID NOT NULL,
    order_date_key INT NOT NULL REFERENCES analytics.dim_date(date_key),
    promised_date_key INT REFERENCES analytics.dim_date(date_key),
    order_status VARCHAR(20) NOT NULL,
    total_order_amount NUMERIC(14,2) NOT NULL CHECK (total_order_amount >= 0),
    order_item_count INT NOT NULL DEFAULT 1 CHECK (order_item_count > 0),
    is_delayed INT NOT NULL DEFAULT 0 CHECK (is_delayed IN (0,1)),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    etl_batch_id VARCHAR(50) NOT NULL
);

-- Grain: 1 record per line item on a purchase order
CREATE TABLE IF NOT EXISTS analytics.fact_order_items (
    order_item_key BIGSERIAL PRIMARY KEY,
    order_id UUID NOT NULL,
    product_key INT NOT NULL REFERENCES analytics.dim_product(product_key),
    customer_key INT NOT NULL REFERENCES analytics.dim_customer(customer_key),
    order_date_key INT NOT NULL REFERENCES analytics.dim_date(date_key),
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0),
    unit_cost NUMERIC(10,2) NOT NULL CHECK (unit_cost >= 0),
    gross_revenue NUMERIC(12,2) NOT NULL CHECK (gross_revenue >= 0),
    discount_amount NUMERIC(10,2) NOT NULL DEFAULT 0.00 CHECK (discount_amount >= 0),
    net_revenue NUMERIC(12,2) NOT NULL CHECK (net_revenue >= 0),
    gross_profit NUMERIC(12,2) NOT NULL,
    etl_batch_id VARCHAR(50) NOT NULL
);

-- Grain: 1 record per product SKU per warehouse location per calendar day
CREATE TABLE IF NOT EXISTS analytics.fact_inventory_daily (
    inventory_snapshot_key BIGSERIAL PRIMARY KEY,
    date_key INT NOT NULL REFERENCES analytics.dim_date(date_key),
    warehouse_key INT NOT NULL REFERENCES analytics.dim_warehouse(warehouse_key),
    product_key INT NOT NULL REFERENCES analytics.dim_product(product_key),
    quantity_on_hand INT NOT NULL CHECK (quantity_on_hand >= 0),
    quantity_allocated INT NOT NULL CHECK (quantity_allocated >= 0),
    quantity_available INT NOT NULL,
    reorder_point INT NOT NULL CHECK (reorder_point >= 0),
    is_out_of_stock INT NOT NULL CHECK (is_out_of_stock IN (0,1)),
    is_low_stock INT NOT NULL CHECK (is_low_stock IN (0,1)),
    etl_batch_id VARCHAR(50) NOT NULL,
    CONSTRAINT uq_fact_inventory_daily UNIQUE (date_key, warehouse_key, product_key)
);

-- Grain: 1 record per machine per 1-minute aggregation interval
CREATE TABLE IF NOT EXISTS analytics.fact_machine_telemetry (
    telemetry_fact_key BIGSERIAL PRIMARY KEY,
    machine_key INT NOT NULL REFERENCES analytics.dim_machine(machine_key),
    timestamp_minute TIMESTAMPTZ NOT NULL,
    date_key INT NOT NULL REFERENCES analytics.dim_date(date_key),
    avg_temperature_c NUMERIC(5,2) NOT NULL,
    max_temperature_c NUMERIC(5,2) NOT NULL,
    avg_vibration_rms NUMERIC(5,2) NOT NULL,
    max_vibration_rms NUMERIC(5,2) NOT NULL,
    avg_pressure_psi NUMERIC(6,2) NOT NULL,
    total_power_kwh NUMERIC(8,4) NOT NULL CHECK (total_power_kwh >= 0),
    reading_count INT NOT NULL CHECK (reading_count > 0),
    etl_batch_id VARCHAR(50) NOT NULL,
    CONSTRAINT uq_fact_telemetry_minute UNIQUE (machine_key, timestamp_minute)
);

-- Grain: 1 record per maintenance event activity
CREATE TABLE IF NOT EXISTS analytics.fact_maintenance_events (
    maintenance_key BIGSERIAL PRIMARY KEY,
    maintenance_id UUID NOT NULL UNIQUE,
    machine_key INT NOT NULL REFERENCES analytics.dim_machine(machine_key),
    performed_date_key INT NOT NULL REFERENCES analytics.dim_date(date_key),
    maintenance_type VARCHAR(30) NOT NULL,
    cost_usd NUMERIC(10,2) NOT NULL CHECK (cost_usd >= 0),
    duration_hours NUMERIC(4,2) NOT NULL DEFAULT 0.00 CHECK (duration_hours >= 0),
    etl_batch_id VARCHAR(50) NOT NULL
);

-- Grain: 1 record per support ticket
CREATE TABLE IF NOT EXISTS analytics.fact_support_tickets (
    ticket_key BIGSERIAL PRIMARY KEY,
    ticket_id UUID NOT NULL UNIQUE,
    customer_key INT NOT NULL REFERENCES analytics.dim_customer(customer_key),
    order_id UUID,
    created_date_key INT NOT NULL REFERENCES analytics.dim_date(date_key),
    resolved_date_key INT REFERENCES analytics.dim_date(date_key),
    priority VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    resolution_time_hours NUMERIC(6,2),
    satisfaction_score INT CHECK (satisfaction_score BETWEEN 1 AND 5),
    interaction_count INT NOT NULL DEFAULT 0 CHECK (interaction_count >= 0),
    etl_batch_id VARCHAR(50) NOT NULL
);
