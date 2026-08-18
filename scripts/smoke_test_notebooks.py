"""
Pre-execution smoke test: test the critical data operations in each notebook
before running nbconvert. Reports what will break.
"""
import sys, io, traceback
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from data_science.db import (
    load_churn_features, load_demand_features, load_inventory_features,
    load_telemetry_features, load_order_items, load_orders, load_support_tickets,
    load_inventory_snapshot,
)

errors = []
passed = []

def test(name, fn):
    try:
        fn()
        passed.append(name)
        print(f"  OK   {name}")
    except Exception as e:
        errors.append((name, str(e)))
        print(f"  FAIL {name}: {e}")

# Load all datasets once
df_orders   = load_orders()
df_items    = load_order_items()
df_tickets  = load_support_tickets()
df_inv      = load_inventory_snapshot()
df_telem    = load_telemetry_features()
df_churn    = load_churn_features()
df_demand   = load_demand_features()
df_inv_ml   = load_inventory_features()
print("All data loaded OK")
print()

# NB01 critical operations
print("=== NB01 Critical Operations ===")

def nb01_revenue():
    monthly = df_items.groupby(df_items["order_date"].dt.to_period("M"))["net_revenue"].sum()
    assert len(monthly) > 0

def nb01_segment():
    seg = df_orders.groupby("customer_segment")["net_amount"].sum()
    assert len(seg) > 0

def nb01_channel():
    # sales_channel doesn't exist — must use channel_id
    ch = df_orders.groupby("channel_id")["net_amount"].sum()
    assert len(ch) > 0

def nb01_inventory():
    below = df_inv["is_below_reorder_point"].sum()
    assert below >= 0

def nb01_telemetry():
    anom = df_telem["temperature_anomaly_flag"].mean()
    assert 0 <= anom <= 1

test("NB01: revenue trend", nb01_revenue)
test("NB01: segment revenue (needs customer_segment)", nb01_segment)
test("NB01: channel via channel_id", nb01_channel)
test("NB01: inventory below reorder", nb01_inventory)
test("NB01: telemetry anomaly flag", nb01_telemetry)

# NB02 critical operations
print("\n=== NB02 Critical Operations ===")

def nb02_churn_rate():
    rate = df_churn["is_churned_target"].mean()
    assert 0 < rate < 1

def nb02_feature_cols():
    cols = ["total_orders","total_revenue","avg_order_value","days_since_last_order",
            "order_frequency_30d","order_frequency_90d","avg_csat_score",
            "total_support_tickets","days_as_customer"]
    missing = [c for c in cols if c not in df_churn.columns]
    if missing:
        raise ValueError(f"Missing feature cols: {missing}")

def nb02_chi_square():
    ct = pd.crosstab(df_churn["customer_segment"], df_churn["is_churned_target"])
    assert ct.shape[0] > 1

def nb02_rfm():
    rfm = df_churn[["days_since_last_order","total_orders","total_revenue","is_churned_target"]].copy()
    rfm["R"] = pd.qcut(rfm["days_since_last_order"], 4, labels=[4,3,2,1], duplicates="drop").astype(float)
    assert rfm["R"].notna().sum() > 0

test("NB02: churn rate", nb02_churn_rate)
test("NB02: feature cols present", nb02_feature_cols)
test("NB02: chi_square segment", nb02_chi_square)
test("NB02: RFM scoring", nb02_rfm)

# NB03 critical operations
print("\n=== NB03 Critical Operations ===")

def nb03_lag_cols():
    for c in ["units_sold_lag7","units_sold_lag14","rolling_avg_7d","units_sold_target"]:
        if c not in df_demand.columns:
            raise ValueError(f"Missing: {c}")

def nb03_date():
    df_demand["sale_date"].dt.to_period("M")

def nb03_stationarity():
    from statsmodels.tsa.stattools import adfuller
    sku = df_demand["product_id"].unique()[0]
    series = df_demand.loc[df_demand["product_id"]==sku, "units_sold_target"].dropna()
    adf = adfuller(series)
    assert adf[1] is not None

test("NB03: lag cols", nb03_lag_cols)
test("NB03: date column", nb03_date)
test("NB03: ADF stationarity", nb03_stationarity)

# NB04 critical operations
print("\n=== NB04 Critical Operations ===")

def nb04_target():
    rate = df_inv_ml["stockout_risk_flag_target"].mean()
    assert 0 <= rate <= 1

def nb04_feature_cols():
    for c in ["quantity_on_hand","quantity_available","reorder_point","stockout_risk_flag_target"]:
        if c not in df_inv_ml.columns:
            raise ValueError(f"Missing: {c}")

def nb04_below():
    # is_below_reorder_point aliased from stockout_risk_flag_target
    val = df_inv_ml["is_below_reorder_point"].sum()
    assert val >= 0

test("NB04: stockout target", nb04_target)
test("NB04: feature cols", nb04_feature_cols)
test("NB04: is_below_reorder_point alias", nb04_below)

# NB05 critical operations
print("\n=== NB05 Critical Operations ===")

def nb05_machine_types():
    types = df_telem["machine_type"].unique()
    assert len(types) >= 3

def nb05_signals():
    for c in ["avg_temperature_c","avg_vibration_rms","avg_pressure_psi","avg_power_kw"]:
        if c not in df_telem.columns:
            raise ValueError(f"Missing: {c}")

def nb05_isolation_forest():
    from sklearn.ensemble import IsolationForest
    sample = df_telem[["avg_temperature_c","avg_vibration_rms","avg_pressure_psi","avg_power_kw"]].dropna().head(1000)
    clf = IsolationForest(contamination=0.05, random_state=42)
    clf.fit(sample)
    scores = clf.decision_function(sample)
    assert len(scores) > 0

test("NB05: machine types", nb05_machine_types)
test("NB05: signal cols", nb05_signals)
test("NB05: isolation forest", nb05_isolation_forest)

# NB06 critical operations
print("\n=== NB06 Critical Operations ===")

def nb06_segment_aov():
    segs = df_orders["customer_segment"].dropna().unique()
    assert len(segs) >= 2

def nb06_csat_issue():
    cats = df_tickets["issue_category"].dropna().unique()
    assert len(cats) >= 2

def nb06_channel_chi():
    # channel_id exists, not sales_channel
    ct = pd.crosstab(df_orders["customer_segment"], df_orders["channel_id"])
    assert ct.shape[0] >= 2

test("NB06: segment AOV", nb06_segment_aov)
test("NB06: CSAT by issue", nb06_csat_issue)
test("NB06: segment vs channel_id", nb06_channel_chi)

print()
print("=" * 60)
print(f"  Passed: {len(passed)}   Failed: {len(errors)}")
if errors:
    print("\n  FAILURES TO FIX:")
    for name, err in errors:
        print(f"    {name}: {err}")
sys.exit(1 if errors else 0)
