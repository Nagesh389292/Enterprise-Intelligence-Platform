-- ==============================================================================
-- Enterprise Intelligence Platform — Database Initialization Script 02
-- Description: Creates 3NF Normalized Source System Tables under 'source' schema
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. CUSTOMER DOMAIN
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS source.customer_segments (
    segment_id SERIAL PRIMARY KEY,
    segment_code VARCHAR(30) NOT NULL UNIQUE,
    segment_name VARCHAR(100) NOT NULL,
    target_annual_revenue NUMERIC(15,2) DEFAULT 0.00 CHECK (target_annual_revenue >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source.customers (
    customer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    industry VARCHAR(100) NOT NULL,
    segment_id INT NOT NULL REFERENCES source.customer_segments(segment_id),
    account_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (account_status IN ('ACTIVE','INACTIVE','CHURNED')),
    contact_email VARCHAR(255) NOT NULL,
    contact_phone VARCHAR(50),
    credit_limit NUMERIC(12,2) NOT NULL DEFAULT 50000.00 CHECK (credit_limit >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source.customer_addresses (
    address_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES source.customers(customer_id) ON DELETE CASCADE,
    address_type VARCHAR(20) NOT NULL DEFAULT 'SHIPPING' CHECK (address_type IN ('BILLING','SHIPPING')),
    street_address VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state_province VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    country_code CHAR(2) NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source.customer_interactions (
    interaction_id BIGSERIAL PRIMARY KEY,
    customer_id UUID NOT NULL REFERENCES source.customers(customer_id) ON DELETE CASCADE,
    channel VARCHAR(30) NOT NULL CHECK (channel IN ('EMAIL','PHONE','PORTAL','IN_PERSON')),
    interaction_type VARCHAR(50) NOT NULL,
    notes TEXT,
    interaction_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------------------------
-- 2. SALES DOMAIN
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS source.sales_channels (
    channel_id SERIAL PRIMARY KEY,
    channel_code VARCHAR(30) NOT NULL UNIQUE,
    channel_name VARCHAR(100) NOT NULL,
    commission_rate NUMERIC(5,4) NOT NULL DEFAULT 0.0000 CHECK (commission_rate BETWEEN 0 AND 1)
);

CREATE TABLE IF NOT EXISTS source.product_categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    parent_category_id INT REFERENCES source.product_categories(category_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source.products (
    product_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku VARCHAR(50) NOT NULL UNIQUE,
    product_name VARCHAR(255) NOT NULL,
    category_id INT NOT NULL REFERENCES source.product_categories(category_id),
    unit_cost NUMERIC(10,2) NOT NULL CHECK (unit_cost >= 0),
    unit_price NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0),
    reorder_point INT NOT NULL DEFAULT 100 CHECK (reorder_point >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source.orders (
    order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number VARCHAR(50) NOT NULL UNIQUE,
    customer_id UUID NOT NULL REFERENCES source.customers(customer_id),
    channel_id INT NOT NULL REFERENCES source.sales_channels(channel_id),
    shipping_address_id UUID NOT NULL REFERENCES source.customer_addresses(address_id),
    order_status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (order_status IN ('PENDING','PROCESSING','SHIPPED','DELIVERED','CANCELLED')),
    order_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    promised_delivery_date DATE,
    total_amount NUMERIC(14,2) NOT NULL DEFAULT 0.00 CHECK (total_amount >= 0)
);

CREATE TABLE IF NOT EXISTS source.order_items (
    order_item_id BIGSERIAL PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES source.orders(order_id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES source.products(product_id),
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0),
    discount_amount NUMERIC(10,2) NOT NULL DEFAULT 0.00 CHECK (discount_amount >= 0),
    total_price NUMERIC(12,2) NOT NULL CHECK (total_price >= 0)
);

-- ------------------------------------------------------------------------------
-- 3. SUPPLY CHAIN DOMAIN
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS source.suppliers (
    supplier_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_code VARCHAR(30) NOT NULL UNIQUE,
    company_name VARCHAR(255) NOT NULL,
    quality_rating NUMERIC(3,2) DEFAULT 5.00 CHECK (quality_rating BETWEEN 0 AND 5),
    lead_time_days INT NOT NULL DEFAULT 14 CHECK (lead_time_days >= 0),
    country_code CHAR(2) NOT NULL
);

CREATE TABLE IF NOT EXISTS source.warehouses (
    warehouse_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    warehouse_code VARCHAR(30) NOT NULL UNIQUE,
    warehouse_name VARCHAR(100) NOT NULL,
    region VARCHAR(50) NOT NULL,
    capacity_sqft INT NOT NULL CHECK (capacity_sqft > 0)
);

CREATE TABLE IF NOT EXISTS source.inventory (
    inventory_id BIGSERIAL PRIMARY KEY,
    warehouse_id UUID NOT NULL REFERENCES source.warehouses(warehouse_id),
    product_id UUID NOT NULL REFERENCES source.products(product_id),
    quantity_on_hand INT NOT NULL DEFAULT 0 CHECK (quantity_on_hand >= 0),
    quantity_allocated INT NOT NULL DEFAULT 0 CHECK (quantity_allocated >= 0),
    last_count_date TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_inventory_wh_product UNIQUE (warehouse_id, product_id)
);

CREATE TABLE IF NOT EXISTS source.inventory_transactions (
    transaction_id BIGSERIAL PRIMARY KEY,
    warehouse_id UUID NOT NULL REFERENCES source.warehouses(warehouse_id),
    product_id UUID NOT NULL REFERENCES source.products(product_id),
    transaction_type VARCHAR(30) NOT NULL CHECK (transaction_type IN ('RECEIPT','SHIPMENT','ADJUSTMENT','TRANSFER')),
    quantity_change INT NOT NULL,
    reference_id VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------------------------
-- 4. OPERATIONS & INDUSTRIAL IOT DOMAIN
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS source.machine_types (
    machine_type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(100) NOT NULL UNIQUE,
    manufacturer VARCHAR(100) NOT NULL,
    max_temperature_c NUMERIC(5,2) NOT NULL DEFAULT 120.00 CHECK (max_temperature_c > 0),
    max_vibration_rms NUMERIC(5,2) NOT NULL DEFAULT 5.00 CHECK (max_vibration_rms > 0)
);

CREATE TABLE IF NOT EXISTS source.machines (
    machine_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    serial_number VARCHAR(100) NOT NULL UNIQUE,
    machine_type_id INT NOT NULL REFERENCES source.machine_types(machine_type_id),
    warehouse_id UUID NOT NULL REFERENCES source.warehouses(warehouse_id),
    installation_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'RUNNING' CHECK (status IN ('RUNNING','MAINTENANCE','OFFLINE','FAILED'))
);

-- RAW INDIVIDUAL TELEMETRY EVENTS
CREATE TABLE IF NOT EXISTS source.machine_telemetry (
    telemetry_id BIGSERIAL PRIMARY KEY,
    machine_id UUID NOT NULL REFERENCES source.machines(machine_id) ON DELETE CASCADE,
    temperature_c NUMERIC(5,2) NOT NULL,
    vibration_rms NUMERIC(5,2) NOT NULL,
    pressure_psi NUMERIC(6,2) NOT NULL,
    power_kw NUMERIC(6,2) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS source.maintenance_events (
    maintenance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    machine_id UUID NOT NULL REFERENCES source.machines(machine_id),
    maintenance_type VARCHAR(30) NOT NULL CHECK (maintenance_type IN ('PREVENTIVE','CORRECTIVE','EMERGENCY')),
    description TEXT NOT NULL,
    technician_name VARCHAR(100) NOT NULL,
    performed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cost_usd NUMERIC(10,2) NOT NULL DEFAULT 0.00 CHECK (cost_usd >= 0)
);

CREATE TABLE IF NOT EXISTS source.failure_events (
    failure_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    machine_id UUID NOT NULL REFERENCES source.machines(machine_id),
    failure_code VARCHAR(50) NOT NULL,
    failure_reason TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    downtime_hours NUMERIC(5,2) NOT NULL DEFAULT 0.00 CHECK (downtime_hours >= 0)
);

-- ------------------------------------------------------------------------------
-- 5. SUPPORT DOMAIN
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS source.support_tickets (
    ticket_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_number VARCHAR(50) NOT NULL UNIQUE,
    customer_id UUID NOT NULL REFERENCES source.customers(customer_id),
    order_id UUID REFERENCES source.orders(order_id),
    issue_category VARCHAR(50) NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM' CHECK (priority IN ('LOW','MEDIUM','HIGH','URGENT')),
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','IN_PROGRESS','RESOLVED','CLOSED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS source.ticket_interactions (
    interaction_id BIGSERIAL PRIMARY KEY,
    ticket_id UUID NOT NULL REFERENCES source.support_tickets(ticket_id) ON DELETE CASCADE,
    sender_type VARCHAR(20) NOT NULL CHECK (sender_type IN ('CUSTOMER','AGENT','SYSTEM')),
    message_text TEXT NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source.customer_satisfaction (
    survey_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL UNIQUE REFERENCES source.support_tickets(ticket_id) ON DELETE CASCADE,
    score INT NOT NULL CHECK (score BETWEEN 1 AND 5),
    feedback_text TEXT,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
