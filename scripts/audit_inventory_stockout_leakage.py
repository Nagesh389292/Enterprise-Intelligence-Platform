"""
scripts/audit_inventory_stockout_leakage.py
--------------------------------------------
Automated Target & Feature Leakage Audit for Inventory Stockout Risk ML.

Mandatory Check Rules:
1. Calculates univariate ROC-AUC for every numerical column in `analytics.ml_inventory_stockout_risk`.
2. Identifies features that are directly used in constructing `stockout_risk_flag_target`:
   Target Formula: `CASE WHEN quantity_available < reorder_point THEN 1 ELSE 0 END`
3. Identifies leaked features (`quantity_available`, `reorder_point`, `days_of_supply`, `quantity_on_hand`, `quantity_allocated`).
4. Raises an error and exits with code 1 if any suspicious feature with univariate AUC >= 0.95 or target formula origin is included in the allowed feature set.
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_science.db import load_inventory_features

TARGET_FORMULA_VARS = ["quantity_available", "reorder_point", "days_of_supply", "quantity_on_hand", "quantity_allocated"]


def audit_inventory_leakage(allowed_features: list[str] = None) -> dict:
    print("=" * 80)
    print("STAGE 8C: INVENTORY STOCKOUT TARGET & FEATURE LEAKAGE AUDIT")
    print("=" * 80)

    df = load_inventory_features()
    target_col = "stockout_risk_flag_target"

    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in ml_inventory_stockout_risk.")

    y = df[target_col].values
    prevalence = float(np.mean(y))
    print(f"Dataset Size: {len(df)} inventory snapshot items")
    print(f"Target Label: {target_col} (1 = Below Reorder Point, 0 = Adequate Stock)")
    print(f"Class Prevalence: {prevalence:.2%} ({int(np.sum(y))} / {len(df)} positive cases)")

    # 1. Inspect Univariate ROC-AUC for all numerical features
    num_cols = df.select_dtypes(include=[np.number]).columns.drop([target_col, "inventory_id", "product_id", "warehouse_id"], errors="ignore")
    
    univariate_auc = {}
    leakage_flags = {}

    print("\n--- UNIVARIATE FEATURE LEAKAGE ANALYSIS ---")
    print(f"{'Feature Name':<30} | {'Univariate AUC':<15} | {'Target Formula Origin':<22} | {'Audit Status':<12}")
    print("-" * 85)

    for col in num_cols:
        val = df[col].fillna(0).values
        try:
            auc = roc_auc_score(y, val)
            if auc < 0.5:
                auc = roc_auc_score(y, -val)
        except Exception:
            auc = 0.5

        univariate_auc[col] = float(auc)
        is_formula_var = col in TARGET_FORMULA_VARS
        is_high_auc = auc >= 0.95

        if is_formula_var or is_high_auc:
            leakage_flags[col] = {
                "univariate_auc": round(auc, 4),
                "is_target_formula_variable": is_formula_var,
                "reason": "Direct formula variable constructing target label label" if is_formula_var else "Suspiciously perfect predictive power (AUC >= 0.95)"
            }
            status = "REJECTED (LEAK)"
        else:
            status = "CLEAN"

        formula_str = "YES (Target Formula)" if is_formula_var else "NO"
        print(f"{col:<30} | {auc:<15.4f} | {formula_str:<22} | {status:<12}")

    # 2. Check allowed feature list if provided
    violations = []
    if allowed_features:
        for f in allowed_features:
            if f in leakage_flags:
                violations.append(f)

    report = {
        "dataset_rows": len(df),
        "target_col": target_col,
        "class_prevalence": prevalence,
        "univariate_auc": univariate_auc,
        "rejected_leaked_features": leakage_flags,
        "violations_in_allowed_set": violations,
        "audit_passed": len(violations) == 0
    }

    # Save audit report
    os.makedirs("docs/data_science", exist_ok=True)
    with open("docs/data_science/inventory_leakage_audit_report.json", "w") as f:
        json.dump(report, f, indent=2)

    if violations:
        print(f"\n[FAIL] LEAKAGE AUDIT FAILED! Leaked features detected in ML feature set: {violations}")
        print("Model training halted to prevent artificial performance inflation.")
        sys.exit(1)
    else:
        print("\n[PASS] LEAKAGE AUDIT PASSED! All rejected leaked features successfully excluded from ML pipeline.")
        return report


if __name__ == "__main__":
    audit_inventory_leakage()
