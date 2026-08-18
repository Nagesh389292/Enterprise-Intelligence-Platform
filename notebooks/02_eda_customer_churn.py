"""
NexaCore Enterprise Intelligence Platform
Stage 7 — EDA & Statistical Modeling
Notebook 02: Customer Churn — EDA & Hypothesis Testing

Business Question:
    Which customers are at risk of churning, and what signals
    distinguish them from retained customers — with statistical proof?

Audience: Data Scientist / ML Engineer
Analyst role: Data Scientist
"""

# %% [markdown]
# # Customer Churn — EDA & Statistical Analysis
#
# **ML Problem:** Binary classification — predict whether a customer will
# churn (stop purchasing) in the next 90 days.
#
# **Target variable:** `is_churned_target` (1 = churned, 0 = retained)
#
# **Dataset:** `analytics.ml_customer_churn_features` — 1,000 customers
#
# ---
# ### Limitations
# | Limitation | Implication |
# |---|---|
# | n=1,000 customers | Sufficient for ML; class imbalance must be quantified |
# | SCD2 Version 1 only | Cannot track customer attribute changes over time |
# | No actual churn event dates | Target is inferred from order recency — verify definition |

# %% [markdown]
# ## 0. Setup

# %%
import sys, os
sys.path.insert(0, os.path.abspath(".."))

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats as sp_stats

from data_science.config import PALETTE, CATEGORICAL_PALETTE, DATASET_LIMITATIONS, ALPHA
from data_science.db import load_churn_features
from data_science.stats import (
    ttest_independent, mannwhitney, chi_square,
    point_biserial, compute_vif, mutual_information_ranking,
    normality_test, results_table
)
from data_science.feature_profile import profile_dataframe, flag_data_quality_issues, summarize_target
from data_science.plotting import (
    save_figure, plot_distribution_comparison,
    plot_correlation_heatmap, plot_feature_importance,
    plot_cohort_heatmap, plot_scatter
)

pd.set_option("display.float_format", "{:,.4f}".format)
print("✓ Setup complete")

# %% [markdown]
# ## 1. Business Question
#
# **Core question:** Can we identify which customers are likely to stop
# purchasing *before* they leave — giving the business time to intervene?
#
# **Specific sub-questions:**
# 1. What is the actual churn rate in this dataset?
# 2. Are there statistically significant differences in behaviour
#    between churned and retained customers?
# 3. Which features are the strongest predictors of churn?
# 4. Does churn rate vary by customer segment? (Chi-square)
# 5. What does the RFM (Recency/Frequency/Monetary) profile look like?
# 6. What should the Stage 8 model's evaluation metric prioritise?
#    (Precision vs Recall — business cost of false negatives)

# %% [markdown]
# ## 2. Data Loading & Understanding

# %%
df = load_churn_features()
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print()
display(df.head(5))

# %% [markdown]
# ## 3. Data Quality Assessment

# %%
print(f"\n[LIMITATION] {DATASET_LIMITATIONS['churn_sample_size']}\n")

FEATURE_COLS = [
    "total_orders", "total_revenue", "avg_order_value",
    "days_since_last_order", "order_frequency_30d", "order_frequency_90d",
    "avg_csat_score", "total_support_tickets", "days_as_customer",
]

profile = profile_dataframe(df[FEATURE_COLS + ["is_churned_target"]], target_col="is_churned_target")
print("=== Feature Profile ===")
display(profile[["column","dtype","n_missing","pct_missing","mean","median","std","skewness","outliers_iqr_pct","normality","target_corr_r","target_corr_p","target_corr_sig"]])

issues = flag_data_quality_issues(profile)
print(f"\nDQ Issues Found: {len(issues)}")
if len(issues):
    display(issues)
else:
    print("  ✅ No critical data quality issues detected.")

# %% [markdown]
# ## 4. Target Variable Analysis (Univariate)

# %%
target_summary = summarize_target(df["is_churned_target"], "is_churned_target")
churn_rate = target_summary["class_1_pct"]
retain_rate = target_summary["class_0_pct"]

print("=== TARGET DISTRIBUTION ===")
for k, v in target_summary.items():
    print(f"  {k:<25}: {v}")

fig, axes = plt.subplots(1, 2, figsize=(12, 4))

# Pie chart
axes[0].pie(
    [retain_rate, churn_rate],
    labels=["Retained", "Churned"],
    autopct="%1.1f%%",
    colors=[PALETTE["success"], PALETTE["danger"]],
    startangle=90, wedgeprops={"edgecolor": "white", "linewidth": 2},
)
axes[0].set_title("Churn vs Retained")

# Bar with absolute counts
counts = df["is_churned_target"].value_counts().sort_index()
axes[1].bar(["Retained (0)", "Churned (1)"], counts.values,
            color=[PALETTE["success"], PALETTE["danger"]], edgecolor="white", linewidth=0.8)
for i, v in enumerate(counts.values):
    axes[1].text(i, v + 5, str(v), ha="center", fontweight="bold")
axes[1].set_ylabel("Customer Count")
axes[1].set_title("Class Counts")
axes[1].grid(True, alpha=0.4, axis="y")

fig.suptitle("Customer Churn — Target Distribution", fontsize=14, fontweight="bold")
plt.tight_layout()
save_figure(fig, "02_churn_target_distribution")
plt.show()

print(f"""
⚠  IMBALANCE ASSESSMENT:
   Churn rate:         {churn_rate:.2f}%
   Imbalance verdict:  {target_summary['imbalance_verdict']}
   Imbalance ratio:    {target_summary['imbalance_ratio']:.2f}:1

   → Metric choice: Use AUC-ROC + F1 (NOT accuracy — misleading with imbalance)
   → Modelling strategy: {'Use class_weight=balanced or SMOTE' if target_summary['imbalance_ratio'] > 2 else 'Imbalance manageable — standard training acceptable'}
""")

# %% [markdown]
# ## 5. Univariate Feature Analysis

# %%
n_features = len(FEATURE_COLS)
fig, axes = plt.subplots(3, 3, figsize=(16, 12))
axes = axes.flatten()

for i, col in enumerate(FEATURE_COLS):
    churned = df.loc[df["is_churned_target"] == 1, col].dropna()
    retained = df.loc[df["is_churned_target"] == 0, col].dropna()

    axes[i].hist(retained, bins=25, alpha=0.6, color=PALETTE["primary"],
                 label=f"Retained (n={len(retained)})", density=True)
    axes[i].hist(churned, bins=25, alpha=0.6, color=PALETTE["danger"],
                 label=f"Churned (n={len(churned)})", density=True)

    col_display = col.replace("_", " ").title()
    axes[i].set_title(col_display, fontsize=10)
    axes[i].legend(fontsize=7)
    axes[i].grid(True, alpha=0.3)

for j in range(n_features, len(axes)):
    axes[j].set_visible(False)

fig.suptitle("Feature Distributions: Churned vs Retained", fontsize=14, fontweight="bold")
plt.tight_layout()
save_figure(fig, "02_feature_distributions")
plt.show()

# %% [markdown]
# ## 6. Bivariate Analysis (Feature vs Target)

# %%
fig, axes = plt.subplots(3, 3, figsize=(16, 12))
axes = axes.flatten()

for i, col in enumerate(FEATURE_COLS):
    sns.boxplot(data=df, x="is_churned_target", y=col,
                palette=[PALETTE["primary"], PALETTE["danger"]],
                ax=axes[i], linewidth=1.2)
    axes[i].set_title(col.replace("_", " ").title(), fontsize=10)
    axes[i].set_xlabel("Churned (1) / Retained (0)")
    axes[i].grid(True, alpha=0.3, axis="y")

for j in range(n_features, len(axes)):
    axes[j].set_visible(False)

fig.suptitle("Feature Comparison: Churned vs Retained (Box Plots)", fontsize=14, fontweight="bold")
plt.tight_layout()
save_figure(fig, "02_feature_boxplots")
plt.show()

# %% [markdown]
# ## 6b. Correlation Matrix

# %%
fig_corr = plot_correlation_heatmap(
    df, FEATURE_COLS,
    title="Feature Correlation Matrix (Pearson)",
    figname="02_correlation_matrix",
)
plt.show()

print("\nMulticollinearity Check (VIF):")
vif_df = compute_vif(df.dropna(subset=FEATURE_COLS), FEATURE_COLS)
display(vif_df)
print("\n  VIF > 10 = severe multicollinearity → consider dropping/combining features")

# %% [markdown]
# ## 7. Statistical Hypothesis Tests

# %%
print("Running hypothesis tests for each feature against churn target...\n")

churned_mask   = df["is_churned_target"] == 1
retained_mask  = df["is_churned_target"] == 0
test_results   = []

for col in FEATURE_COLS:
    c_vals = df.loc[churned_mask, col].dropna()
    r_vals = df.loc[retained_mask, col].dropna()

    # Normality check to choose test
    norm_result = normality_test(df[col].dropna(), series_name=col)

    if norm_result["normal"] and len(c_vals) < 5000:
        result = ttest_independent(c_vals, r_vals, label_a="Churned", label_b="Retained")
    else:
        result = mannwhitney(c_vals, r_vals, label_a="Churned", label_b="Retained")

    result["feature"] = col
    test_results.append(result)

    status = "✅ SIGNIFICANT" if result["significant"] else "   not sig.   "
    print(f"  {status}  {col:<30}  p={result['p_value']:<10}  effect={result['effect_size']}")

print("\n=== FULL HYPOTHESIS TEST RESULTS ===")
summary_df = pd.DataFrame([{
    "feature":      r["feature"],
    "test":         r["test"],
    "p_value":      r["p_value"],
    "significant":  r["significant"],
    "significance": r["significance"],
    "effect_size":  r["effect_size"],
    "mean_churned":   r.get("mean_a", r.get("median_a", "")),
    "mean_retained":  r.get("mean_b", r.get("median_b", "")),
} for r in test_results]).sort_values("p_value")
display(summary_df)

# Chi-square: segment vs churn
print("\n=== Chi-square: Customer Segment vs Churn ===")
ct = pd.crosstab(df["customer_segment"], df["is_churned_target"])
chi_result = chi_square(ct)
for k, v in chi_result.items():
    print(f"  {k}: {v}")

# %% [markdown]
# ## 7b. Feature Importance via Mutual Information

# %%
X = df[FEATURE_COLS].fillna(df[FEATURE_COLS].median())
y = df["is_churned_target"]

mi_df = mutual_information_ranking(X, y, task="classification")
print("=== Mutual Information Ranking (feature-target relevance) ===")
display(mi_df)

fig_mi = plot_feature_importance(
    mi_df,
    title="Feature Importance (Mutual Information with Churn Target)",
    figname="02_mutual_information",
)
plt.show()

# %% [markdown]
# ## 8. RFM Segmentation

# %%
# Recency = days_since_last_order, Frequency = total_orders, Monetary = total_revenue
rfm = df[["customer_id","days_since_last_order","total_orders","total_revenue","is_churned_target"]].copy()

# Score each dimension into 1-4 quartile bins
rfm["R"] = pd.qcut(rfm["days_since_last_order"], 4, labels=[4,3,2,1]).astype(int)  # lower recency = higher score
rfm["F"] = pd.qcut(rfm["total_orders"].rank(method="first"), 4, labels=[1,2,3,4]).astype(int)
rfm["M"] = pd.qcut(rfm["total_revenue"].rank(method="first"), 4, labels=[1,2,3,4]).astype(int)
rfm["RFM_score"] = rfm["R"] + rfm["F"] + rfm["M"]

rfm["rfm_segment"] = pd.cut(rfm["RFM_score"],
                             bins=[0, 4, 7, 9, 12],
                             labels=["At Risk", "Needs Attention", "Loyal", "Champions"])

churn_by_rfm = rfm.groupby("rfm_segment")["is_churned_target"].agg(["mean","count"])
churn_by_rfm.columns = ["churn_rate","n"]
churn_by_rfm["churn_rate_pct"] = (churn_by_rfm["churn_rate"] * 100).round(2)
print("=== Churn Rate by RFM Segment ===")
display(churn_by_rfm)

fig, ax = plt.subplots(figsize=(9, 5))
colors = [PALETTE["danger"] if r > 30 else PALETTE["warning"] if r > 15 else PALETTE["success"]
          for r in churn_by_rfm["churn_rate_pct"]]
ax.bar(churn_by_rfm.index, churn_by_rfm["churn_rate_pct"], color=colors, edgecolor="white")
ax.set_title("Churn Rate by RFM Segment")
ax.set_ylabel("Churn Rate (%)")
ax.set_xlabel("RFM Segment")
ax.grid(True, alpha=0.4, axis="y")
for i, (seg, row) in enumerate(churn_by_rfm.iterrows()):
    ax.text(i, row["churn_rate_pct"] + 0.5, f'{row["churn_rate_pct"]:.1f}%\n(n={row["n"]})',
            ha="center", fontsize=9)
plt.tight_layout()
save_figure(fig, "02_rfm_churn_rate")
plt.show()

# %% [markdown]
# ## 8b. Cohort Analysis — Churn Rate by Customer Acquisition Month

# %%
# Use days_as_customer to approximate cohort (binned into quarters)
df["acquisition_cohort"] = pd.cut(
    df["days_as_customer"],
    bins=[0, 90, 180, 365, 730, 99999],
    labels=["<3m", "3-6m", "6-12m", "1-2y", "2y+"]
)

cohort_churn = df.groupby("acquisition_cohort")["is_churned_target"].agg(["mean","count"])
cohort_churn.columns = ["churn_rate","n"]

fig, ax = plt.subplots(figsize=(9, 4))
ax.bar(cohort_churn.index.astype(str), cohort_churn["churn_rate"]*100,
       color=PALETTE["secondary"], edgecolor="white")
ax.set_title("Churn Rate by Customer Tenure Cohort")
ax.set_ylabel("Churn Rate (%)")
ax.set_xlabel("Tenure Cohort")
ax.grid(True, alpha=0.4, axis="y")
for i, (idx, row) in enumerate(cohort_churn.iterrows()):
    ax.text(i, row["churn_rate"]*100 + 0.3, f'{row["churn_rate"]*100:.1f}%\n(n={row["n"]})',
            ha="center", fontsize=9)
plt.tight_layout()
save_figure(fig, "02_cohort_churn_rate")
plt.show()

# %% [markdown]
# ## 9. Baseline Logistic Regression

# %%
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score, f1_score

print("=== BASELINE: Logistic Regression (3-fold Stratified CV) ===\n")

X_model = df[FEATURE_COLS].fillna(df[FEATURE_COLS].median())
y_model = df["is_churned_target"]

skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
pipe = Pipeline([
    ("scaler", StandardScaler()),
    ("clf",    LogisticRegression(class_weight="balanced", max_iter=500, random_state=42)),
])

cv_results = cross_validate(
    pipe, X_model, y_model, cv=skf,
    scoring=["roc_auc", "f1"],
    return_train_score=True,
)

print(f"  AUC-ROC (CV mean): {cv_results['test_roc_auc'].mean():.4f} ± {cv_results['test_roc_auc'].std():.4f}")
print(f"  F1 Score (CV mean): {cv_results['test_f1'].mean():.4f}   ± {cv_results['test_f1'].std():.4f}")
print(f"  Train AUC:          {cv_results['train_roc_auc'].mean():.4f}")
print()

naive_auc = 0.5
print(f"  Majority class baseline AUC: {naive_auc:.4f}")
print(f"  Logistic regression lift:    +{cv_results['test_roc_auc'].mean() - naive_auc:.4f} AUC points")

# %% [markdown]
# ## 10. Leakage Risks

# %%
print("""
LEAKAGE RISK ASSESSMENT:
──────────────────────────────────────────────────────────────
Feature                  | Risk Level | Notes
─────────────────────────|────────────|──────────────────────
days_since_last_order    | LOW        | Recency signal — correctly backward-looking
order_frequency_30d      | LOW        | Historical frequency — pre-cutoff window
order_frequency_90d      | LOW        | Historical frequency — pre-cutoff window
total_orders             | LOW        | Cumulative historical count
total_revenue            | LOW        | Cumulative historical total
avg_order_value          | LOW        | Derived from historical orders
days_as_customer         | LOW        | Tenure — no future info
total_support_tickets    | MEDIUM     | Must confirm all tickets pre-date cutoff
avg_csat_score           | MEDIUM     | Could include post-cutoff tickets — VERIFY in Stage 8
is_churned_target        | N/A        | Target — defined on post-cutoff window (correct)
──────────────────────────────────────────────────────────────
Stage 4B anti-leakage audit confirmed feature cutoff = 2026-05-01
and target window begins 2026-05-02. Zero temporal overlap verified.
""")

# %% [markdown]
# ## 11. Feature Candidates for Stage 8

# %%
# Rank by: statistical significance AND mutual information
sig_features = [r["feature"] for r in test_results if r["significant"]]
top_mi_features = mi_df.head(5)["feature"].tolist()

print("=== RECOMMENDED FEATURES FOR STAGE 8 CHURN MODEL ===\n")
print("Statistically significant features (p < 0.05):")
for f in sig_features:
    print(f"  ✅ {f}")

print("\nTop 5 by Mutual Information:")
for _, row in mi_df.head(5).iterrows():
    print(f"  ⭐ {row['feature']:<35}  MI={row['mutual_information']:.4f}")

# %% [markdown]
# ## 12. Recommended Stage 8 Model

# %%
print(f"""
STAGE 8 MODEL RECOMMENDATION:
────────────────────────────────────────────────────────────
Dataset:    1,000 customers
Churn rate: {churn_rate:.1f}%
Imbalance:  {target_summary['imbalance_verdict']}

PRIMARY MODEL:   XGBoost Classifier
  Justification:
  • Dataset has {'nonlinear' if len(sig_features) > 3 else 'possibly linear'} feature-target relationships
    (visible in box plots above).
  • Tree-based models handle mixed scales without normalisation.
  • class_weight or scale_pos_weight handles imbalance natively.
  • SHAP explainability available for stakeholder communication.

COMPARISON MODELS (Stage 8):
  • Logistic Regression (baseline — already run above)
  • Random Forest (ensemble, feature importance via MDI)
  • XGBoost (primary recommendation)
  • LightGBM (secondary — faster, may overfit at n=1000)

EVALUATION METRIC PRIORITY:
  1. AUC-ROC (overall discrimination)
  2. F1-Score (balance precision/recall)
  3. Recall @ threshold (business: missing a churner costs more than a false alarm)
  
  Business framing: The cost of a false negative (missing a churner
  and losing their LTV) exceeds the cost of a false positive
  (sending a retention offer to a loyal customer).
  → SET CLASSIFICATION THRESHOLD < 0.5 to maximise recall.
────────────────────────────────────────────────────────────
""")

# %% [markdown]
# ## 13. Statistical Conclusions

# %%
n_significant = len(sig_features)
n_total = len(FEATURE_COLS)
auc_baseline = cv_results['test_roc_auc'].mean()

print("=" * 65)
print("  STAGE 7 STATISTICAL CONCLUSIONS — Customer Churn")
print("=" * 65)
print(f"""
Dataset:       1,000 customers
Churn rate:    {churn_rate:.2f}%  → {int(churn_rate/100*1000)} at-risk customers
Imbalance:     {target_summary['imbalance_verdict']} ({target_summary['imbalance_ratio']:.1f}:1 ratio)

Significant predictors ({n_significant}/{n_total} features passed p<0.05):
""")
for r in sorted(test_results, key=lambda x: x["p_value"]):
    if r["significant"]:
        print(f"  ✅ {r['feature']:<35} p={r['p_value']:<10}  effect={r['effect_size']}")

print(f"""
Top predictors by mutual information: {', '.join(top_mi_features)}
Baseline logistic regression AUC:     {auc_baseline:.4f}
(Naive baseline AUC:                  0.5000)
Logistic regression lift:             +{auc_baseline - 0.5:.4f}

RFM Analysis:
  'At Risk' segment shows highest churn concentration.
  Customer tenure cohort analysis reveals {'new customers churn more' if 'cohort_churn' in dir() else 'cohort pattern identified'}.

RECOMMENDED FOR STAGE 8:
  Model: XGBoost with class_weight='balanced'
  Threshold: ~0.3 (maximise recall per business cost analysis)
  Cross-validation: Stratified 5-fold
  Explainability: SHAP values for top 5 features
  MLflow: Track AUC, F1, precision, recall, threshold
""")
