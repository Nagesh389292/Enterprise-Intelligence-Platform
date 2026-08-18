"""
Probe script: verify every table and column that the 6 notebooks query.
Exits 0 if all checks pass, 1 if any fail.
Run: python scripts/probe_schema.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

from data_science.config import CONTROL_TOTALS
from data_science.db import get_engine
from sqlalchemy import text

engine = get_engine()
errors = []
ok     = []

def check(label, sql):
    try:
        with engine.connect() as c:
            r = c.execute(text(sql)).fetchall()
        ok.append(f"  OK   {label}")
    except Exception as e:
        errors.append(f"  FAIL {label} >> {e}")

# Table existence
TABLES = [
    "analytics.ml_customer_churn_features",
    "analytics.ml_demand_forecasting_daily",
    "analytics.ml_inventory_stockout_risk",
    "analytics.ml_machine_telemetry_features",
    "analytics.fact_order_items",
    "analytics.fact_orders",
    "analytics.fact_support_tickets",
    "analytics.fact_inventory_snapshot",
    "analytics.dim_customer",
    "analytics.dim_product",
    "analytics.dim_warehouse",
    "analytics.dim_machine",
]
for t in TABLES:
    check(f"exists {t}", f"SELECT COUNT(*) FROM {t} LIMIT 1")

# Key column existence
COL_CHECKS = {
    "analytics.ml_customer_churn_features": [
        "customer_id","total_orders","total_revenue","avg_order_value",
        "days_since_last_order","order_frequency_30d","order_frequency_90d",
        "avg_csat_score","total_support_tickets","days_as_customer","is_churned_target"
    ],
    "analytics.ml_demand_forecasting_daily": [
        "product_id","date_key","units_sold_lag7","units_sold_lag14",
        "rolling_avg_7d","units_sold_target"
    ],
    "analytics.ml_inventory_stockout_risk": [
        "inventory_id","product_id","warehouse_id","quantity_on_hand",
        "quantity_allocated","quantity_available","reorder_point",
        "is_below_reorder_point","stockout_risk_flag_target"
    ],
    "analytics.ml_machine_telemetry_features": [
        "machine_id","date_key","avg_temperature_c","max_temperature_c",
        "min_temperature_c","avg_vibration_rms","max_vibration_rms",
        "avg_pressure_psi","avg_power_kw","temperature_anomaly_flag",
        "vibration_anomaly_flag","event_count"
    ],
    "analytics.fact_order_items": [
        "order_id","product_id","date_key","quantity","unit_price",
        "discount_amount","gross_revenue","net_revenue","gross_profit_margin"
    ],
    "analytics.fact_orders": [
        "order_id","customer_id","date_key","order_status","payment_method",
        "sales_channel","total_amount","discount_amount","net_amount"
    ],
    "analytics.fact_support_tickets": [
        "ticket_id","customer_id","date_key","issue_category","priority",
        "status","csat_score"
    ],
    "analytics.fact_inventory_snapshot": [
        "inventory_id","warehouse_id","product_id","date_key","quantity_on_hand",
        "quantity_allocated","quantity_available","reorder_point","is_below_reorder_point"
    ],
    "analytics.dim_customer": ["customer_id","customer_segment","city","state","country"],
    "analytics.dim_product": ["product_id","product_name","category_name"],
    "analytics.dim_warehouse": ["warehouse_id","warehouse_name","city"],
    "analytics.dim_machine": ["machine_id","machine_type","warehouse_id"],
}
for table, cols in COL_CHECKS.items():
    col_list = ", ".join(cols)
    check(f"cols {table}", f"SELECT {col_list} FROM {table} LIMIT 0")

# Row count verification
COUNTS = {
    "analytics.ml_customer_churn_features":  CONTROL_TOTALS["churn_feature_rows"],
    "analytics.ml_demand_forecasting_daily": CONTROL_TOTALS["demand_forecast_rows"],
    "analytics.ml_inventory_stockout_risk":  CONTROL_TOTALS["stockout_risk_rows"],
    "analytics.fact_orders":                 CONTROL_TOTALS["total_orders"],
    "analytics.fact_support_tickets":        CONTROL_TOTALS["support_tickets"],
}
for table, expected in COUNTS.items():
    with engine.connect() as c:
        actual = c.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
    label = f"rowcount {table.split('.')[-1]}"
    if actual == expected:
        ok.append(f"  OK   {label} = {actual:,} (matches canonical {expected:,})")
    else:
        errors.append(f"  MISMATCH {label}: actual={actual:,}  canonical={expected:,}")

# Telemetry count
with engine.connect() as c:
    tel_count = c.execute(text("SELECT COUNT(*) FROM analytics.ml_machine_telemetry_features")).scalar()
ok.append(f"  INFO telemetry rows = {tel_count:,}  (canonical: {CONTROL_TOTALS['telemetry_records']:,})")

# Live control totals from DB
print("=================================================================")
print("  LIVE CONTROL TOTALS FROM DB")
print("=================================================================")
live_checks = {
    "net_revenue":      "SELECT ROUND(SUM(net_revenue)::numeric, 2) FROM analytics.fact_order_items",
    "gross_revenue":    "SELECT ROUND(SUM(gross_revenue)::numeric, 2) FROM analytics.fact_order_items",
    "total_units":      "SELECT SUM(quantity) FROM analytics.fact_order_items",
    "total_orders":     "SELECT COUNT(DISTINCT order_id) FROM analytics.fact_orders",
    "avg_csat":         "SELECT ROUND(AVG(csat_score)::numeric, 2) FROM analytics.fact_support_tickets",
    "inventory_oh":     "SELECT SUM(quantity_on_hand) FROM analytics.fact_inventory_snapshot",
    "low_stock":        "SELECT COUNT(*) FROM analytics.fact_inventory_snapshot WHERE is_below_reorder_point = true",
}
live_vals = {}
for name, sql in live_checks.items():
    with engine.connect() as c:
        live_vals[name] = c.execute(text(sql)).scalar()
    print(f"  {name:<18}: {live_vals[name]}")

print()
print("=================================================================")
print("  SCHEMA PROBE RESULTS")
print("=================================================================")
for line in ok:
    print(line)
if errors:
    print()
    print("  FAILURES:")
    for line in errors:
        print(line)
print()
print(f"  Passed: {len(ok)}   Failed: {len(errors)}")
sys.exit(1 if errors else 0)
