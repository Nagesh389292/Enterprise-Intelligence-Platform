"""Verify all db.py loaders execute and return expected row counts."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from data_science.db import (
    load_churn_features, load_demand_features, load_inventory_features,
    load_telemetry_features, load_order_items, load_orders,
    load_support_tickets, load_inventory_snapshot,
)
from data_science.config import CONTROL_TOTALS

errors = []

def test_loader(name, fn, expected_rows=None, key_cols=None):
    try:
        df = fn()
        cols_ok = all(c in df.columns for c in (key_cols or []))
        status = "OK"
        detail = f"rows={len(df):,}  cols={list(df.columns[:6])}{'...' if len(df.columns)>6 else ''}"
        if expected_rows and len(df) != expected_rows:
            status = "WARN"
            detail += f"  EXPECTED {expected_rows:,}"
        if not cols_ok:
            missing = [c for c in (key_cols or []) if c not in df.columns]
            status = "FAIL"
            detail += f"  MISSING COLS: {missing}"
            errors.append(f"{name}: missing cols {missing}")
        print(f"  {status:<5} {name:<35} {detail}")
        return df
    except Exception as e:
        print(f"  FAIL  {name:<35} EXCEPTION: {e}")
        errors.append(f"{name}: {e}")
        return None

print("=" * 75)
print("  DB LOADER VERIFICATION")
print("=" * 75)

df_churn = test_loader("load_churn_features", load_churn_features,
    expected_rows=CONTROL_TOTALS["churn_feature_rows"],
    key_cols=["customer_id","total_orders","days_since_last_order","is_churned_target","customer_segment"])

df_demand = test_loader("load_demand_features", load_demand_features,
    expected_rows=CONTROL_TOTALS["demand_forecast_rows"],
    key_cols=["product_id","units_sold_target","units_sold_lag7","rolling_avg_7d","sale_date"])

df_inv = test_loader("load_inventory_features", load_inventory_features,
    expected_rows=CONTROL_TOTALS["stockout_risk_rows"],
    key_cols=["product_id","quantity_available","reorder_point","stockout_risk_flag_target"])

df_tel = test_loader("load_telemetry_features", load_telemetry_features,
    key_cols=["machine_id","machine_type","avg_temperature_c","avg_vibration_rms","anomaly_severity_score"])

df_items = test_loader("load_order_items", load_order_items,
    key_cols=["order_id","product_id","net_revenue","gross_revenue"])

df_orders = test_loader("load_orders", load_orders,
    expected_rows=CONTROL_TOTALS["total_orders"],
    key_cols=["order_id","customer_id","net_amount","customer_segment"])

df_tickets = test_loader("load_support_tickets", load_support_tickets,
    expected_rows=CONTROL_TOTALS["support_tickets"],
    key_cols=["ticket_id","csat_score","issue_category","customer_segment"])

test_loader("load_inventory_snapshot", load_inventory_snapshot,
    key_cols=["inventory_id","warehouse_id","product_id","quantity_on_hand","is_below_reorder_point"])

print()
if df_churn is not None:
    churn_rate = df_churn["is_churned_target"].mean()
    print(f"  Churn rate:        {churn_rate*100:.2f}%")
    print(f"  Churned customers: {df_churn['is_churned_target'].sum()}")
    print(f"  Churn segments:    {df_churn.groupby('customer_segment')['is_churned_target'].mean().round(3).to_dict()}")
    print(f"  Feature cutoff:    {df_churn['feature_cutoff_date'].iloc[0]}")

if df_demand is not None:
    print(f"\n  Demand date range: {df_demand['sale_date'].min()} to {df_demand['sale_date'].max()}")
    print(f"  Unique products:   {df_demand['product_id'].nunique()}")
    print(f"  Lag7 non-null:     {df_demand['units_sold_lag7'].notna().sum():,}")

if df_tel is not None:
    print(f"\n  Telemetry rows:    {len(df_tel):,}")
    print(f"  Unique machines:   {df_tel['machine_id'].nunique()}")
    print(f"  Machine types:     {df_tel['machine_type'].unique()}")

print()
print(f"  Total errors: {len(errors)}")
if errors:
    for e in errors:
        print(f"    {e}")
sys.exit(1 if errors else 0)
