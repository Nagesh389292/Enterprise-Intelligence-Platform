-- =============================================================================
-- Enterprise Intelligence Platform - Stage 9 MLOps Prediction Store DDL
-- Schema: analytics
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS analytics;

-- 1. Fact Predictions: Customer Churn (Stage 8A)
CREATE TABLE IF NOT EXISTS analytics.fact_predictions_customer_churn (
    prediction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR(50) NOT NULL,
    prediction_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    churn_probability DOUBLE PRECISION NOT NULL,
    predicted_churn_flag INTEGER NOT NULL,
    risk_tier VARCHAR(20) NOT NULL, -- Low, Medium, High
    model_version VARCHAR(50) NOT NULL,
    run_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pred_churn_customer_id ON analytics.fact_predictions_customer_churn(customer_id);
CREATE INDEX IF NOT EXISTS idx_pred_churn_timestamp ON analytics.fact_predictions_customer_churn(prediction_timestamp);

-- 2. Fact Predictions: SKU Demand Forecasting (Stage 8B)
CREATE TABLE IF NOT EXISTS analytics.fact_predictions_sku_demand (
    prediction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id VARCHAR(50) NOT NULL,
    forecast_date DATE NOT NULL,
    prediction_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    predicted_demand_units DOUBLE PRECISION NOT NULL,
    lower_bound_95 DOUBLE PRECISION,
    upper_bound_95 DOUBLE PRECISION,
    model_version VARCHAR(50) NOT NULL,
    run_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pred_demand_product_date ON analytics.fact_predictions_sku_demand(product_id, forecast_date);

-- 3. Fact Predictions: Inventory Stockout Risk (Stage 8C)
CREATE TABLE IF NOT EXISTS analytics.fact_predictions_inventory_stockout (
    prediction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id VARCHAR(50) NOT NULL,
    prediction_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    stockout_risk_prob_7d DOUBLE PRECISION NOT NULL,
    stockout_alert_flag_7d INTEGER NOT NULL,
    risk_severity VARCHAR(20) NOT NULL, -- Low, Moderate, Critical
    model_version VARCHAR(50) NOT NULL,
    run_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pred_stockout_item_id ON analytics.fact_predictions_inventory_stockout(item_id);
CREATE INDEX IF NOT EXISTS idx_pred_stockout_timestamp ON analytics.fact_predictions_inventory_stockout(prediction_timestamp);

-- 4. Fact Predictions: Machine Health & Telemetry Failure (Stage 8D)
CREATE TABLE IF NOT EXISTS analytics.fact_predictions_machine_health (
    prediction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    machine_id VARCHAR(50) NOT NULL,
    minute_timestamp TIMESTAMPTZ NOT NULL,
    prediction_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    anomaly_score DOUBLE PRECISION NOT NULL,
    is_anomaly_flag INTEGER NOT NULL,
    failure_prob_24h DOUBLE PRECISION NOT NULL,
    failure_alert_flag_24h INTEGER NOT NULL,
    health_status VARCHAR(20) NOT NULL, -- Normal, Warning, Critical
    model_version VARCHAR(50) NOT NULL,
    run_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pred_machine_id_time ON analytics.fact_predictions_machine_health(machine_id, minute_timestamp);
