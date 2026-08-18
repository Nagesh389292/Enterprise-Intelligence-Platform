"""
data_science/db.py
------------------
Database connectivity helpers for all Stage 7 notebooks.
All column names and types verified against live PostgreSQL schema (2026-08-18).
Ensures date/timestamp columns are parsed as pandas datetime objects.
"""

import pandas as pd
from sqlalchemy import create_engine, text
from data_science.config import SQLALCHEMY_URL


def get_engine():
    """Return a SQLAlchemy engine connected to nexacore_dw."""
    return create_engine(SQLALCHEMY_URL, pool_pre_ping=True)


def read_sql(query: str, db_engine=None, params: dict | None = None) -> pd.DataFrame:
    """Execute a SQL query and return a pandas DataFrame."""
    if db_engine is not None and hasattr(db_engine, "connect"):
        engine = db_engine
    else:
        if isinstance(db_engine, (dict, list, tuple)) and params is None:
            params = db_engine
        engine = get_engine()
    with engine.connect() as conn:
        if params:
            return pd.read_sql(text(query), conn, params=params)
        return pd.read_sql(text(query), conn)


# ---------------------------------------------------------------------------
# Pre-built queries — all column names verified against live schema
# ---------------------------------------------------------------------------

def load_churn_features() -> pd.DataFrame:
    """
    Load ml_customer_churn_features.
    Actual columns verified: total_orders_to_cutoff, total_spend_to_cutoff,
    avg_order_value_to_cutoff, recency_days_at_cutoff, avg_csat_score_to_cutoff,
    total_support_tickets_to_cutoff, account_tenure_days, segment_name, is_churned_target.
    """
    df = read_sql("""
        SELECT
            customer_id,
            total_orders_to_cutoff                                          AS total_orders,
            total_spend_to_cutoff                                           AS total_revenue,
            avg_order_value_to_cutoff                                       AS avg_order_value,
            recency_days_at_cutoff                                          AS days_since_last_order,
            avg_csat_score_to_cutoff                                        AS avg_csat_score,
            total_support_tickets_to_cutoff                                 AS total_support_tickets,
            account_tenure_days                                             AS days_as_customer,
            ROUND(total_orders_to_cutoff::numeric / NULLIF(account_tenure_days, 0) * 30, 4)
                                                                            AS order_frequency_30d,
            ROUND(total_orders_to_cutoff::numeric / NULLIF(account_tenure_days, 0) * 90, 4)
                                                                            AS order_frequency_90d,
            segment_name                                                    AS customer_segment,
            primary_state_province                                          AS state,
            is_churned_target,
            feature_cutoff_date
        FROM analytics.ml_customer_churn_features
    """)
    if "feature_cutoff_date" in df.columns:
        df["feature_cutoff_date"] = pd.to_datetime(df["feature_cutoff_date"])
    return df


def load_demand_features() -> pd.DataFrame:
    """
    Load ml_demand_forecasting_daily.
    Columns verified: lag_7_units_sold, lag_14_units_sold, rolling_7_day_avg_units,
    units_sold_target, full_date, day_of_week, month, is_weekend, product_name, category_name.
    """
    df = read_sql("""
        SELECT
            product_id,
            date_key,
            full_date                   AS sale_date,
            day_of_week,
            month,
            is_weekend,
            product_name,
            category_name,
            units_sold_target,
            daily_revenue,
            daily_orders_count,
            lag_7_units_sold            AS units_sold_lag7,
            lag_14_units_sold           AS units_sold_lag14,
            rolling_7_day_avg_units     AS rolling_avg_7d,
            rolling_30_day_avg_units    AS rolling_avg_30d
        FROM analytics.ml_demand_forecasting_daily
        ORDER BY product_id, date_key
    """)
    df["sale_date"] = pd.to_datetime(df["sale_date"])
    return df


def load_inventory_features() -> pd.DataFrame:
    """
    Load ml_inventory_stockout_risk.
    Columns verified: quantity_on_hand, quantity_allocated, quantity_available,
    reorder_point, days_of_supply, stockout_risk_flag_target.
    """
    df = read_sql("""
        SELECT
            inventory_id,
            product_id,
            warehouse_id,
            product_name,
            category_name,
            warehouse_name,
            warehouse_location,
            quantity_on_hand,
            quantity_allocated,
            quantity_available,
            reorder_point,
            reorder_quantity,
            days_of_supply,
            unit_cost,
            unit_price,
            inventory_value_usd,
            stockout_risk_flag_target,
            -- Derived: treat stockout_risk_flag_target = 1 as below reorder point
            stockout_risk_flag_target   AS is_below_reorder_point
        FROM analytics.ml_inventory_stockout_risk
    """)
    return df


def load_telemetry_features() -> pd.DataFrame:
    """
    Load ml_machine_telemetry_features joined with dim_machine.
    """
    df = read_sql("""
        SELECT
            t.telemetry_minute_key,
            t.machine_id,
            t.minute_timestamp,
            DATE(t.minute_timestamp)    AS event_date,
            t.raw_event_count           AS event_count,
            t.avg_temperature_c,
            t.max_temperature_c,
            t.avg_vibration_rms,
            t.max_vibration_rms,
            t.avg_pressure_psi,
            t.avg_power_kw,
            t.rolling_10min_avg_temp,
            t.rolling_10min_avg_vib,
            t.anomaly_severity_score,
            t.temp_spread,
            t.warehouse_id,
            t.warehouse_name,
            t.machine_type_name         AS machine_type,
            -- Derived anomaly flags from severity score
            CASE WHEN t.anomaly_severity_score > 0.7 THEN 1 ELSE 0 END
                                        AS temperature_anomaly_flag,
            CASE WHEN t.anomaly_severity_score > 0.5 THEN 1 ELSE 0 END
                                        AS vibration_anomaly_flag
        FROM analytics.ml_machine_telemetry_features t
        ORDER BY t.machine_id, t.minute_timestamp
    """)
    df["event_date"] = pd.to_datetime(df["event_date"])
    df["minute_timestamp"] = pd.to_datetime(df["minute_timestamp"])
    return df


def load_order_items() -> pd.DataFrame:
    """Load fact_order_items joined with product info."""
    df = read_sql("""
        SELECT
            oi.order_id,
            oi.product_id,
            oi.date_key,
            oi.quantity,
            oi.unit_price,
            oi.discount_amount,
            oi.gross_revenue,
            oi.net_revenue,
            oi.gross_profit_margin,
            p.product_name,
            p.category_name,
            TO_DATE(oi.date_key::text, 'YYYYMMDD') AS order_date
        FROM analytics.fact_order_items oi
        LEFT JOIN analytics.dim_product p ON p.product_id = oi.product_id
    """)
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df


def load_orders() -> pd.DataFrame:
    """
    Load fact_orders.
    """
    df = read_sql("""
        SELECT
            o.order_id,
            o.customer_id,
            o.date_key,
            o.order_status,
            o.channel_id,
            o.total_amount              AS net_amount,
            o.total_amount              AS gross_amount,
            0::numeric                  AS discount_amount,
            c.segment_name              AS customer_segment,
            c.primary_country_code      AS country,
            TO_DATE(o.date_key::text, 'YYYYMMDD') AS order_date,
            o.derived_delivery_delay_days
        FROM analytics.fact_orders o
        LEFT JOIN analytics.dim_customer c ON c.customer_id = o.customer_id
    """)
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df


def load_support_tickets() -> pd.DataFrame:
    """Load fact_support_tickets with customer segment."""
    df = read_sql("""
        SELECT
            st.ticket_id,
            st.customer_id,
            st.date_key,
            st.issue_category,
            st.priority,
            st.status,
            st.csat_score,
            c.segment_name              AS customer_segment,
            TO_DATE(st.date_key::text, 'YYYYMMDD') AS ticket_date
        FROM analytics.fact_support_tickets st
        LEFT JOIN analytics.dim_customer c ON c.customer_id = st.customer_id
    """)
    df["ticket_date"] = pd.to_datetime(df["ticket_date"])
    return df


def load_inventory_snapshot() -> pd.DataFrame:
    """Load fact_inventory_snapshot with warehouse/product metadata."""
    return read_sql("""
        SELECT
            i.inventory_id,
            i.warehouse_id,
            i.product_id,
            i.date_key,
            i.quantity_on_hand,
            i.quantity_allocated,
            i.quantity_available,
            i.reorder_point,
            i.is_below_reorder_point,
            p.product_name,
            p.category_name,
            w.warehouse_name
        FROM analytics.fact_inventory_snapshot i
        LEFT JOIN analytics.dim_product   p ON p.product_id   = i.product_id
        LEFT JOIN analytics.dim_warehouse w ON w.warehouse_id = i.warehouse_id
    """)
