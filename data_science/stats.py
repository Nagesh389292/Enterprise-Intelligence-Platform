"""
data_science/stats.py
---------------------
Reusable statistical test wrappers for Stage 7 notebooks.
Each function returns a structured result dict so notebooks
can render consistent tables without boilerplate.

All tests use alpha = 0.05 by default (from config.ALPHA).
"""

import numpy as np
import pandas as pd
from scipy import stats as sp_stats
from data_science.config import ALPHA, EFFECT_SMALL, EFFECT_MEDIUM, EFFECT_LARGE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _effect_label(d: float) -> str:
    d = abs(d)
    if d < EFFECT_SMALL:
        return "negligible"
    elif d < EFFECT_MEDIUM:
        return "small"
    elif d < EFFECT_LARGE:
        return "medium"
    return "large"


def _sig_label(p: float, alpha: float = ALPHA) -> str:
    if p < 0.001:
        return "*** (p<0.001)"
    elif p < 0.01:
        return "**  (p<0.01)"
    elif p < alpha:
        return "*   (p<0.05)"
    return "ns  (not significant)"


# ---------------------------------------------------------------------------
# 1. Independent samples t-test
# ---------------------------------------------------------------------------

def ttest_independent(group_a: pd.Series, group_b: pd.Series,
                       label_a: str = "Group A", label_b: str = "Group B",
                       alpha: float = ALPHA) -> dict:
    """
    Welch's independent t-test for difference of means.
    Returns structured result dict.
    """
    a = group_a.dropna()
    b = group_b.dropna()
    t_stat, p_val = sp_stats.ttest_ind(a, b, equal_var=False)

    # Cohen's d
    pooled_std = np.sqrt((a.std() ** 2 + b.std() ** 2) / 2)
    cohens_d = (a.mean() - b.mean()) / pooled_std if pooled_std > 0 else 0.0

    return {
        "test": "Welch's independent t-test",
        "label_a": label_a,
        "label_b": label_b,
        "n_a": len(a),
        "n_b": len(b),
        "mean_a": round(a.mean(), 4),
        "mean_b": round(b.mean(), 4),
        "t_statistic": round(t_stat, 4),
        "p_value": round(p_val, 6),
        "significant": p_val < alpha,
        "significance": _sig_label(p_val, alpha),
        "cohens_d": round(cohens_d, 4),
        "effect_size": _effect_label(cohens_d),
    }


# ---------------------------------------------------------------------------
# 2. Mann-Whitney U test (non-parametric alternative to t-test)
# ---------------------------------------------------------------------------

def mannwhitney(group_a: pd.Series, group_b: pd.Series,
                label_a: str = "Group A", label_b: str = "Group B",
                alpha: float = ALPHA) -> dict:
    """Mann-Whitney U test for difference in distributions."""
    a = group_a.dropna()
    b = group_b.dropna()
    u_stat, p_val = sp_stats.mannwhitneyu(a, b, alternative="two-sided")

    # Rank-biserial correlation as effect size
    n = len(a) * len(b)
    r = 1 - (2 * u_stat) / n if n > 0 else 0.0

    return {
        "test": "Mann-Whitney U",
        "label_a": label_a,
        "label_b": label_b,
        "n_a": len(a),
        "n_b": len(b),
        "median_a": round(float(a.median()), 4),
        "median_b": round(float(b.median()), 4),
        "u_statistic": round(u_stat, 4),
        "p_value": round(p_val, 6),
        "significant": p_val < alpha,
        "significance": _sig_label(p_val, alpha),
        "rank_biserial_r": round(r, 4),
        "effect_size": _effect_label(abs(r)),
    }


# ---------------------------------------------------------------------------
# 3. Chi-square test of independence
# ---------------------------------------------------------------------------

def chi_square(observed: pd.DataFrame, alpha: float = ALPHA) -> dict:
    """
    Chi-square test of independence on a contingency table.
    `observed` should be a crosstab DataFrame.
    """
    chi2, p_val, dof, expected = sp_stats.chi2_contingency(observed)
    n = observed.values.sum()
    cramers_v = np.sqrt(chi2 / (n * (min(observed.shape) - 1))) if n > 0 else 0.0

    return {
        "test": "Chi-square test of independence",
        "chi2_statistic": round(chi2, 4),
        "degrees_of_freedom": dof,
        "p_value": round(p_val, 6),
        "significant": p_val < alpha,
        "significance": _sig_label(p_val, alpha),
        "cramers_v": round(cramers_v, 4),
        "effect_size": _effect_label(cramers_v),
    }


# ---------------------------------------------------------------------------
# 4. One-way ANOVA
# ---------------------------------------------------------------------------

def anova_oneway(*groups, group_labels=None, alpha: float = ALPHA) -> dict:
    """One-way ANOVA across three or more groups."""
    clean = [pd.Series(g).dropna() for g in groups]
    f_stat, p_val = sp_stats.f_oneway(*clean)

    # Eta-squared (effect size for ANOVA)
    grand_mean = np.concatenate([g.values for g in clean]).mean()
    ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in clean)
    ss_total   = sum(((g - grand_mean) ** 2).sum() for g in clean)
    eta_sq = ss_between / ss_total if ss_total > 0 else 0.0

    labels = group_labels or [f"Group {i+1}" for i in range(len(groups))]
    return {
        "test": "One-way ANOVA",
        "groups": labels,
        "group_sizes": [len(g) for g in clean],
        "group_means": [round(float(g.mean()), 4) for g in clean],
        "f_statistic": round(f_stat, 4),
        "p_value": round(p_val, 6),
        "significant": p_val < alpha,
        "significance": _sig_label(p_val, alpha),
        "eta_squared": round(eta_sq, 4),
        "effect_size": _effect_label(np.sqrt(eta_sq)),
    }


# ---------------------------------------------------------------------------
# 5. Kruskal-Wallis test (non-parametric ANOVA)
# ---------------------------------------------------------------------------

def kruskal_wallis(*groups, group_labels=None, alpha: float = ALPHA) -> dict:
    """Kruskal-Wallis H test for difference across 3+ groups."""
    clean = [pd.Series(g).dropna() for g in groups]
    h_stat, p_val = sp_stats.kruskal(*clean)
    labels = group_labels or [f"Group {i+1}" for i in range(len(groups))]
    return {
        "test": "Kruskal-Wallis H test",
        "groups": labels,
        "group_sizes": [len(g) for g in clean],
        "group_medians": [round(float(g.median()), 4) for g in clean],
        "h_statistic": round(h_stat, 4),
        "p_value": round(p_val, 6),
        "significant": p_val < alpha,
        "significance": _sig_label(p_val, alpha),
    }


# ---------------------------------------------------------------------------
# 6. Augmented Dickey-Fuller stationarity test
# ---------------------------------------------------------------------------

def adf_test(series: pd.Series, series_name: str = "series",
             alpha: float = ALPHA) -> dict:
    """ADF test for stationarity. Null = unit root (non-stationary)."""
    from statsmodels.tsa.stattools import adfuller
    series = series.dropna()
    result = adfuller(series, autolag="AIC")
    adf_stat, p_val, lags, nobs, crit_vals, _ = result
    stationary = p_val < alpha
    return {
        "test": "Augmented Dickey-Fuller",
        "series": series_name,
        "adf_statistic": round(adf_stat, 4),
        "p_value": round(p_val, 6),
        "lags_used": lags,
        "n_observations": nobs,
        "critical_values": {k: round(v, 4) for k, v in crit_vals.items()},
        "stationary": stationary,
        "verdict": "STATIONARY" if stationary else "NON-STATIONARY",
    }


# ---------------------------------------------------------------------------
# 7. Normality test (Shapiro-Wilk, capped at n=5000)
# ---------------------------------------------------------------------------

def normality_test(series: pd.Series, series_name: str = "series",
                   alpha: float = ALPHA) -> dict:
    """Shapiro-Wilk for n<5000, D'Agostino-Pearson for larger samples."""
    s = series.dropna()
    if len(s) <= 5000:
        stat, p_val = sp_stats.shapiro(s)
        test_name = "Shapiro-Wilk"
    else:
        stat, p_val = sp_stats.normaltest(s)
        test_name = "D'Agostino-Pearson"
    return {
        "test": test_name,
        "series": series_name,
        "n": len(s),
        "statistic": round(float(stat), 4),
        "p_value": round(float(p_val), 6),
        "significant": p_val < alpha,
        "normal": p_val >= alpha,
        "verdict": "NORMAL" if p_val >= alpha else "NOT NORMAL",
    }


# ---------------------------------------------------------------------------
# 8. Point-biserial correlation (continuous vs binary target)
# ---------------------------------------------------------------------------

def point_biserial(continuous: pd.Series, binary: pd.Series,
                   feature_name: str = "feature") -> dict:
    """Point-biserial correlation between a continuous feature and binary target."""
    mask = continuous.notna() & binary.notna()
    r, p_val = sp_stats.pointbiserialr(binary[mask], continuous[mask])
    return {
        "test": "Point-biserial correlation",
        "feature": feature_name,
        "r": round(r, 4),
        "p_value": round(p_val, 6),
        "significant": p_val < ALPHA,
        "significance": _sig_label(p_val),
        "direction": "positive" if r > 0 else "negative",
    }


# ---------------------------------------------------------------------------
# 9. VIF (Variance Inflation Factor) for multicollinearity
# ---------------------------------------------------------------------------

def compute_vif(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """
    Compute VIF for each feature in feature_cols.
    VIF > 10 indicates severe multicollinearity.
    """
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    X = df[feature_cols].dropna()
    vif_data = pd.DataFrame({
        "feature": feature_cols,
        "VIF": [
            round(variance_inflation_factor(X.values, i), 2)
            for i in range(len(feature_cols))
        ],
    })
    vif_data["multicollinearity"] = vif_data["VIF"].apply(
        lambda v: "severe (>10)" if v > 10
        else ("moderate (5-10)" if v > 5 else "low (<5)")
    )
    return vif_data.sort_values("VIF", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 10. Mutual information (feature-target relevance)
# ---------------------------------------------------------------------------

def mutual_information_ranking(X: pd.DataFrame, y: pd.Series,
                                task: str = "classification") -> pd.DataFrame:
    """
    Rank features by mutual information with target.
    task = 'classification' | 'regression'
    """
    from sklearn.feature_selection import (
        mutual_info_classif, mutual_info_regression
    )
    X_clean = X.dropna()
    y_clean = y[X_clean.index]
    if task == "classification":
        mi = mutual_info_classif(X_clean, y_clean, random_state=42)
    else:
        mi = mutual_info_regression(X_clean, y_clean, random_state=42)
    return pd.DataFrame({
        "feature": X.columns,
        "mutual_information": mi,
    }).sort_values("mutual_information", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 11. Summary table renderer
# ---------------------------------------------------------------------------

def results_table(results: list[dict]) -> pd.DataFrame:
    """Convert a list of test result dicts to a clean summary DataFrame."""
    rows = []
    for r in results:
        stat_val = (
            r.get("t_statistic") or
            r.get("u_statistic") or
            r.get("chi2_statistic") or
            r.get("f_statistic") or
            r.get("h_statistic") or
            r.get("adf_statistic") or
            r.get("r", "")
        )
        rows.append({
            "Test": r.get("test", ""),
            "Variable": r.get("feature", r.get("series", r.get("label_a", ""))),
            "Statistic": stat_val,
            "p-value": r.get("p_value", ""),
            "Significance": r.get("significance", ""),
            "Effect Size": r.get("effect_size", r.get("cohens_d", "")),
        })
    return pd.DataFrame(rows)
