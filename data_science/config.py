"""
data_science/config.py
----------------------
Central configuration for all Stage 7 notebooks.
Defines DB connection, canonical control totals, colour palette,
figure export settings, and dataset limitations.
"""

import os

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DB_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
    "port": int(os.environ.get("POSTGRES_PORT", "5433")),
    "user": os.environ.get("POSTGRES_USER", "nexacore_admin"),
    "password": os.environ.get("POSTGRES_PASSWORD", "nexacore_secret_pass"),
    "dbname": os.environ.get("POSTGRES_DB", "nexacore_dw"),
}

SQLALCHEMY_URL = (
    f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
)

# ---------------------------------------------------------------------------
# Canonical control totals (ingestion batch batch_20260818_013615_ee055b)
# ---------------------------------------------------------------------------
CONTROL_TOTALS = {
    "net_revenue":        77_237_960.93,
    "gross_revenue":      83_513_938.52,
    "total_discounts":     6_275_977.59,
    "total_units":           192_575,
    "total_orders":           10_000,
    "total_order_items":      35_193,
    "total_customers":         1_000,
    "avg_csat":                 3.38,
    "inventory_on_hand":     210_174,
    "low_stock_items":             85,
    "fleet_machines":              50,
    "telemetry_records":      100_000,
    "support_tickets":          2_500,
    "churn_feature_rows":       1_000,
    "demand_forecast_rows":    18_100,
    "stockout_risk_rows":         400,
    "telemetry_feature_rows": 100_000,
}

# ---------------------------------------------------------------------------
# Dataset limitations — must be referenced in each notebook
# ---------------------------------------------------------------------------
DATASET_LIMITATIONS = {
    "maintenance_events": (
        "Only 3 maintenance event records exist. Supervised predictive "
        "maintenance is not feasible. Stage 7 frames this as unsupervised "
        "anomaly detection using telemetry signals."
    ),
    "inventory_grain": (
        "fact_inventory_snapshot contains 400 point-in-time records on a "
        "single snapshot date (2026-06-30). This is NOT a daily time-series. "
        "Stockout risk analysis is cross-sectional, not longitudinal."
    ),
    "scd2_history": (
        "snp_customers contains Version-1 records only (point-in-time snapshot). "
        "No customer attribute history is available before the initial load."
    ),
    "churn_sample_size": (
        "1,000 customer records. With a churn rate to be determined by EDA, "
        "the minority class may be small. Evaluate class balance before "
        "choosing evaluation metrics (prefer F1/AUC over accuracy)."
    ),
    "stockout_sample_size": (
        "400 inventory records. Sufficient for EDA and simple classifiers "
        "(logistic regression, decision tree). Insufficient for deep learning "
        "or complex ensemble methods without augmentation."
    ),
}

# ---------------------------------------------------------------------------
# Brand colour palette (consistent across all notebooks)
# ---------------------------------------------------------------------------
PALETTE = {
    "primary":    "#1B4F72",   # deep navy
    "secondary":  "#2E86AB",   # ocean blue
    "accent":     "#A8DADC",   # light teal
    "warning":    "#E9C46A",   # amber
    "danger":     "#E63946",   # coral red
    "success":    "#2A9D8F",   # emerald
    "neutral":    "#6C757D",   # slate grey
    "background": "#F8F9FA",   # off-white
    "text":       "#212529",   # near-black
}

SEQUENTIAL_PALETTE = "Blues"
DIVERGING_PALETTE  = "RdBu_r"
CATEGORICAL_PALETTE = [
    PALETTE["primary"], PALETTE["secondary"], PALETTE["success"],
    PALETTE["warning"], PALETTE["danger"], PALETTE["accent"],
]

# ---------------------------------------------------------------------------
# Figure export
# ---------------------------------------------------------------------------
PROJECT_ROOT  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIGURES_DIR   = os.path.join(PROJECT_ROOT, "docs", "data_science", "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

FIGURE_DPI    = 150
FIGURE_FORMAT = "png"

# ---------------------------------------------------------------------------
# Significance thresholds
# ---------------------------------------------------------------------------
ALPHA         = 0.05       # standard significance level
EFFECT_SMALL  = 0.2        # Cohen's d small effect
EFFECT_MEDIUM = 0.5        # Cohen's d medium effect
EFFECT_LARGE  = 0.8        # Cohen's d large effect
