"""
data_science/feature_profile.py
--------------------------------
Automated feature profiling functions for Stage 7 notebooks.
Generates a structured summary of any DataFrame — missing values,
distributions, outliers, skewness, cardinality — in one call.
"""

import numpy as np
import pandas as pd
from scipy import stats as sp_stats


def profile_dataframe(df: pd.DataFrame, target_col: str | None = None) -> pd.DataFrame:
    """
    Generate a full feature profile for every column in df.

    Returns a DataFrame with one row per column and the following metrics:
    dtype, n_missing, pct_missing, n_unique, min, max, mean, median, std,
    skewness, kurtosis, iqr, outliers_iqr_pct, normality_verdict (if numeric).

    If target_col is given, numeric features also include
    point-biserial / Pearson correlation with the target.
    """
    records = []
    for col in df.columns:
        series = df[col]
        rec = {
            "column":      col,
            "dtype":       str(series.dtype),
            "n":           len(series),
            "n_missing":   series.isna().sum(),
            "pct_missing": round(series.isna().mean() * 100, 2),
            "n_unique":    series.nunique(),
        }

        if pd.api.types.is_numeric_dtype(series):
            s = series.dropna()
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr    = q3 - q1
            lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            outliers_pct = round(((s < lo) | (s > hi)).mean() * 100, 2)

            # Normality (Shapiro-Wilk if n<=5000, else D'Agostino-Pearson)
            if len(s) >= 3:
                if len(s) <= 5000:
                    _, p_norm = sp_stats.shapiro(s)
                else:
                    _, p_norm = sp_stats.normaltest(s)
                normal_verdict = "normal" if p_norm >= 0.05 else "not normal"
            else:
                p_norm, normal_verdict = None, "n/a"

            rec.update({
                "min":              round(float(s.min()), 4),
                "max":              round(float(s.max()), 4),
                "mean":             round(float(s.mean()), 4),
                "median":           round(float(s.median()), 4),
                "std":              round(float(s.std()), 4),
                "skewness":         round(float(s.skew()), 4),
                "kurtosis":         round(float(s.kurtosis()), 4),
                "q1":               round(float(q1), 4),
                "q3":               round(float(q3), 4),
                "iqr":              round(float(iqr), 4),
                "outliers_iqr_pct": outliers_pct,
                "normality_p":      round(p_norm, 4) if p_norm is not None else None,
                "normality":        normal_verdict,
            })

            if target_col and target_col in df.columns:
                target = df[target_col]
                mask = s.index.intersection(target.dropna().index)
                if len(mask) > 2:
                    if pd.api.types.is_numeric_dtype(target) and target.nunique() == 2:
                        # binary target → point-biserial
                        r, p = sp_stats.pointbiserialr(target[mask], s[mask])
                    else:
                        # continuous target → Pearson
                        r, p = sp_stats.pearsonr(s[mask], target[mask])
                    rec["target_corr_r"] = round(float(r), 4)
                    rec["target_corr_p"] = round(float(p), 6)
                    rec["target_corr_sig"] = "yes" if p < 0.05 else "no"
        else:
            # Categorical / object column
            top = series.value_counts()
            rec.update({
                "top_value":        str(top.index[0]) if len(top) > 0 else None,
                "top_value_count":  int(top.iloc[0]) if len(top) > 0 else None,
                "top_value_pct":    round(top.iloc[0] / len(series) * 100, 2) if len(top) > 0 else None,
            })

        records.append(rec)

    return pd.DataFrame(records)


def flag_data_quality_issues(profile: pd.DataFrame,
                             missing_threshold: float = 5.0,
                             outlier_threshold: float = 5.0,
                             high_skew_threshold: float = 2.0) -> pd.DataFrame:
    """
    Given a profile DataFrame (from profile_dataframe), flag columns
    with potential data quality issues.

    Returns a DataFrame listing only flagged columns with the issue type.
    """
    issues = []
    for _, row in profile.iterrows():
        col_issues = []
        if row["pct_missing"] > missing_threshold:
            col_issues.append(f"HIGH MISSING: {row['pct_missing']}%")
        if "outliers_iqr_pct" in row and pd.notna(row.get("outliers_iqr_pct")):
            if row["outliers_iqr_pct"] > outlier_threshold:
                col_issues.append(f"OUTLIERS: {row['outliers_iqr_pct']}% IQR outliers")
        if "skewness" in row and pd.notna(row.get("skewness")):
            if abs(row["skewness"]) > high_skew_threshold:
                col_issues.append(f"SKEWED: {row['skewness']:.2f}")
        if "n_unique" in row and row["n_unique"] == 1:
            col_issues.append("CONSTANT: only 1 unique value")
        if col_issues:
            issues.append({
                "column": row["column"],
                "dtype":  row["dtype"],
                "issues": " | ".join(col_issues),
            })
    return pd.DataFrame(issues) if issues else pd.DataFrame(
        columns=["column", "dtype", "issues"]
    )


def summarize_target(series: pd.Series, target_name: str = "target") -> dict:
    """
    Summarize a binary or continuous target variable for framing the ML problem.
    """
    s = series.dropna()
    is_binary = s.nunique() == 2

    summary = {
        "target":    target_name,
        "n":         len(s),
        "n_missing": series.isna().sum(),
        "n_unique":  s.nunique(),
        "dtype":     str(s.dtype),
    }
    if is_binary:
        vc = s.value_counts(normalize=True).sort_index()
        summary["type"] = "binary"
        summary["class_0_pct"] = round(float(vc.iloc[0]) * 100, 2) if len(vc) > 0 else None
        summary["class_1_pct"] = round(float(vc.iloc[1]) * 100, 2) if len(vc) > 1 else None
        ratio = vc.iloc[0] / vc.iloc[1] if vc.iloc[1] > 0 else float("inf")
        summary["imbalance_ratio"] = round(float(ratio), 2)
        summary["imbalance_verdict"] = (
            "severe (>10:1)" if ratio > 10 else
            "moderate (5:1-10:1)" if ratio > 5 else
            "mild (2:1-5:1)" if ratio > 2 else "balanced (<2:1)"
        )
    else:
        summary["type"] = "continuous"
        summary["mean"]   = round(float(s.mean()), 4)
        summary["median"] = round(float(s.median()), 4)
        summary["std"]    = round(float(s.std()), 4)
        summary["min"]    = round(float(s.min()), 4)
        summary["max"]    = round(float(s.max()), 4)

    return summary
