-- ==============================================================================
-- Enterprise Intelligence Platform — Database Initialization Script 05
-- Description: Creates Targeted B-Tree Performance Indexes across Source & Analytics schemas
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. SOURCE SCHEMA INDEXES
-- ------------------------------------------------------------------------------

-- Customer Lookups & Status Filtering
CREATE INDEX IF NOT EXISTS idx_source_customers_segment ON source.customers (segment_id);
CREATE INDEX IF NOT EXISTS idx_source_customers_status ON source.customers (account_status);
CREATE INDEX IF NOT EXISTS idx_source_customers_email ON source.customers (contact_email);
CREATE INDEX IF NOT EXISTS idx_source_cust_addr_customer ON source.customer_addresses (customer_id, address_type);
CREATE INDEX IF NOT EXISTS idx_source_cust_interactions_lookup ON source.customer_interactions (customer_id, interaction_timestamp);

-- Product Catalog Lookups
CREATE INDEX IF NOT EXISTS idx_source_products_sku ON source.products (sku);
CREATE INDEX IF NOT EXISTS idx_source_products_category ON source.products (category_id);

-- Sales & Orders Lookups
CREATE INDEX IF NOT EXISTS idx_source_orders_customer ON source.orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_source_orders_timestamp ON source.orders (order_timestamp);
CREATE INDEX IF NOT EXISTS idx_source_orders_status ON source.orders (order_status);
CREATE INDEX IF NOT EXISTS idx_source_order_items_composite ON source.order_items (order_id, product_id);

-- Inventory & Stock Tracking
CREATE INDEX IF NOT EXISTS idx_source_inventory_product_wh ON source.inventory (product_id, warehouse_id);
CREATE INDEX IF NOT EXISTS idx_source_inventory_trans_lookup ON source.inventory_transactions (warehouse_id, product_id, created_at);

-- Operations & Machine Telemetry (Raw Event Time-Series Pruning)
CREATE INDEX IF NOT EXISTS idx_source_machines_facility ON source.machines (warehouse_id, status);
CREATE INDEX IF NOT EXISTS idx_source_telemetry_machine_time ON source.machine_telemetry (machine_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_source_maintenance_machine ON source.maintenance_events (machine_id, performed_at);
CREATE INDEX IF NOT EXISTS idx_source_failures_machine ON source.failure_events (machine_id, occurred_at);

-- Support Tickets
CREATE INDEX IF NOT EXISTS idx_source_tickets_customer ON source.support_tickets (customer_id);
CREATE INDEX IF NOT EXISTS idx_source_tickets_status ON source.support_tickets (status, priority);

-- ------------------------------------------------------------------------------
-- 2. ANALYTICS SCHEMA INDEXES
-- ------------------------------------------------------------------------------

-- Dimension Natural Key Lookups
CREATE INDEX IF NOT EXISTS idx_analytics_dim_cust_id ON analytics.dim_customer (customer_id, is_current);
CREATE INDEX IF NOT EXISTS idx_analytics_dim_prod_sku ON analytics.dim_product (sku);
CREATE INDEX IF NOT EXISTS idx_analytics_dim_machine_id ON analytics.dim_machine (machine_id, is_current);
CREATE INDEX IF NOT EXISTS idx_analytics_dim_date_full ON analytics.dim_date (full_date);

-- Fact Orders Aggregations
CREATE INDEX IF NOT EXISTS idx_analytics_fact_orders_date ON analytics.fact_orders (order_date_key);
CREATE INDEX IF NOT EXISTS idx_analytics_fact_orders_cust ON analytics.fact_orders (customer_key);

-- Fact Order Items Aggregations
CREATE INDEX IF NOT EXISTS idx_analytics_fact_order_items_prod ON analytics.fact_order_items (product_key);
CREATE INDEX IF NOT EXISTS idx_analytics_fact_order_items_date ON analytics.fact_order_items (order_date_key);
CREATE INDEX IF NOT EXISTS idx_analytics_fact_order_items_cust ON analytics.fact_order_items (customer_key);

-- Fact Inventory Daily Snapshot Aggregations
CREATE INDEX IF NOT EXISTS idx_analytics_fact_inv_daily_date_wh ON analytics.fact_inventory_daily (date_key, warehouse_key);
CREATE INDEX IF NOT EXISTS idx_analytics_fact_inv_daily_prod ON analytics.fact_inventory_daily (product_key);

-- Fact Machine Telemetry Minute Aggregations
CREATE INDEX IF NOT EXISTS idx_analytics_fact_telem_machine_time ON analytics.fact_machine_telemetry (machine_key, timestamp_minute DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_fact_telem_date ON analytics.fact_machine_telemetry (date_key);

-- Fact Maintenance & Tickets
CREATE INDEX IF NOT EXISTS idx_analytics_fact_maint_machine ON analytics.fact_maintenance_events (machine_key, performed_date_key);
CREATE INDEX IF NOT EXISTS idx_analytics_fact_tickets_cust ON analytics.fact_support_tickets (customer_key, created_date_key);

-- ------------------------------------------------------------------------------
-- 3. AUDIT SCHEMA INDEXES
-- ------------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_audit_exec_batch ON audit.pipeline_execution_logs (etl_batch_id);
CREATE INDEX IF NOT EXISTS idx_audit_dq_batch ON audit.data_quality_audit_logs (etl_batch_id, table_name);
CREATE INDEX IF NOT EXISTS idx_audit_quarantine_batch ON audit.quarantine_records (etl_batch_id, source_table);
