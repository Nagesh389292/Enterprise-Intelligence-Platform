"""Introspect actual column names for all mismatched tables."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from data_science.db import get_engine
from sqlalchemy import text

engine = get_engine()

tables = [
    "analytics.ml_customer_churn_features",
    "analytics.ml_demand_forecasting_daily",
    "analytics.ml_inventory_stockout_risk",
    "analytics.ml_machine_telemetry_features",
    "analytics.fact_orders",
    "analytics.dim_customer",
    "analytics.dim_warehouse",
    "analytics.dim_machine",
]

for t in tables:
    schema, tname = t.split(".")
    sql = (
        "SELECT column_name, data_type FROM information_schema.columns "
        f"WHERE table_schema='{schema}' AND table_name='{tname}' "
        "ORDER BY ordinal_position"
    )
    with engine.connect() as c:
        rows = c.execute(text(sql)).fetchall()
    print(f"\n=== {t} ===")
    for col, dtype in rows:
        print(f"  {col:<45} {dtype}")
