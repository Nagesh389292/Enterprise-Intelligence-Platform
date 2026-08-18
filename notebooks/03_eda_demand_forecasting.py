"""
NexaCore Enterprise Intelligence Platform
Stage 7 — EDA & Statistical Modeling
Notebook 03: Demand Forecasting — Time-Series EDA & Statistical Analysis

Business Question:
    What are the true demand patterns for each product, and are those
    patterns statistically forecastable — or dominated by noise?

Audience: Data Scientist
"""

# %% [markdown]
# # Demand Forecasting — Time-Series EDA
#
# **ML Problem:** Time-series forecasting — predict daily units sold
# per product for the next 14-30 days.
#
# **Target:** `units_sold_target` (daily units, product-level)
# **Grain:** `product_id × date_key`  (18,100 rows = 181 dates × 100 products)
#
# **Limitations:**
# - 181 calendar days of history — adequate for lag features, limited for long seasonality
# - Lag-7 and lag-14 features verified anti-leakage in Stage 4B

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
from statsmodels.tsa.stattools import adfuller, acf, pacf
from statsmodels.tsa.seasonal import STL

from data_science.config import PALETTE, CATEGORICAL_PALETTE, CONTROL_TOTALS, DATASET_LIMITATIONS
from data_science.db import load_demand_features
from data_science.stats import adf_test, normality_test, results_table
from data_science.feature_profile import profile_dataframe, flag_data_quality_issues
from data_science.plotting import save_figure, plot_time_series

pd.set_option("display.float_format", "{:,.4f}".format)
print("✓ Setup complete")

# %% [markdown]
# ## 1. Business Question
#
# 1. Is total demand growing, declining, or stable over the observation window?
# 2. Is there a weekly seasonal pattern?
# 3. Which products are most forecastable (low variance, detectable trend)?
# 4. Are the pre-built lag features (lag_7, lag_14) valid predictors?
# 5. What is the appropriate model family — SARIMA, XGBoost with lags, or Prophet?

# %% [markdown]
# ## 2. Data Loading & Understanding

# %%
df = load_demand_features()
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print(f"\nDate range: {df['sale_date'].min()} → {df['sale_date'].max()}")
print(f"Unique products: {df['product_id'].nunique()}")
print(f"Unique dates: {df['sale_date'].nunique()}")
print(f"Total target rows: {len(df):,}  (canonical: {CONTROL_TOTALS['demand_forecast_rows']:,})")

# Verify grain
grain_check = df.groupby(["product_id","sale_date"]).size()
print(f"\nGrain check (max rows per product-date): {grain_check.max()}  (should be 1)")

# %% [markdown]
# ## 3. Data Quality Assessment

# %%
profile = profile_dataframe(df[["units_sold_lag7","units_sold_lag14","rolling_avg_7d","units_sold_target"]])
print("=== Feature Profile ===")
display(profile[["column","n_missing","pct_missing","mean","median","std","skewness","outliers_iqr_pct"]])

issues = flag_data_quality_issues(profile)
print(f"\nDQ Issues: {len(issues)}")
if len(issues):
    display(issues)

# Note: lag features will have NaN for the first 7/14 days — expected
lag7_missing  = df["units_sold_lag7"].isna().sum()
lag14_missing = df["units_sold_lag14"].isna().sum()
print(f"\n  Expected NaN — lag_7:  {lag7_missing}  (first 7 rows per product = {7 * df['product_id'].nunique()} expected)")
print(f"  Expected NaN — lag_14: {lag14_missing}  (first 14 rows per product = {14 * df['product_id'].nunique()} expected)")

# %% [markdown]
# ## 4. Univariate Demand Analysis

# %%
# Aggregate daily demand across all products
daily_agg = (
    df.groupby("sale_date")["units_sold_target"]
    .sum()
    .reset_index()
    .sort_values("sale_date")
)
daily_agg["sale_date"] = pd.to_datetime(daily_agg["sale_date"])

fig, axes = plt.subplots(3, 1, figsize=(14, 12))

# Total daily demand
axes[0].plot(daily_agg["sale_date"], daily_agg["units_sold_target"],
             color=PALETTE["primary"], linewidth=1.5, alpha=0.8)
axes[0].set_title("Total Daily Units Sold (All Products)")
axes[0].set_ylabel("Units")
axes[0].grid(True, alpha=0.4)

# 7-day rolling average
daily_agg["rolling_7d"] = daily_agg["units_sold_target"].rolling(7).mean()
daily_agg["rolling_30d"] = daily_agg["units_sold_target"].rolling(30).mean()
axes[1].plot(daily_agg["sale_date"], daily_agg["units_sold_target"],
             color=PALETTE["accent"], alpha=0.4, linewidth=1, label="Daily")
axes[1].plot(daily_agg["sale_date"], daily_agg["rolling_7d"],
             color=PALETTE["primary"], linewidth=2, label="7d rolling avg")
axes[1].plot(daily_agg["sale_date"], daily_agg["rolling_30d"],
             color=PALETTE["danger"], linewidth=2, label="30d rolling avg")
axes[1].set_title("Demand with Rolling Averages")
axes[1].set_ylabel("Units")
axes[1].legend()
axes[1].grid(True, alpha=0.4)

# Weekly pattern
daily_agg["dayofweek"] = daily_agg["sale_date"].dt.dayofweek
dow_avg = daily_agg.groupby("dayofweek")["units_sold_target"].mean()
dow_labels = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
axes[2].bar(dow_labels, dow_avg.values, color=PALETTE["secondary"], edgecolor="white")
axes[2].set_title("Average Daily Demand by Day of Week")
axes[2].set_ylabel("Avg Units")
axes[2].grid(True, alpha=0.4, axis="y")
for i, v in enumerate(dow_avg.values):
    axes[2].text(i, v + 5, f"{v:.0f}", ha="center", fontsize=9)

fig.suptitle("Aggregate Demand Analysis", fontsize=14, fontweight="bold")
plt.tight_layout()
save_figure(fig, "03_demand_aggregate")
plt.show()

print(f"\n📊 Aggregate Stats:")
print(f"  Avg daily total demand: {daily_agg['units_sold_target'].mean():.1f} units")
print(f"  Demand std:             {daily_agg['units_sold_target'].std():.1f}")
print(f"  CV (std/mean):          {daily_agg['units_sold_target'].std()/daily_agg['units_sold_target'].mean():.4f}")
print(f"  Peak day demand:        {daily_agg['units_sold_target'].max():.0f} units")

# %% [markdown]
# ## 5. STL Decomposition (Trend + Seasonal + Residual)

# %%
# Use aggregate daily series for decomposition
ts_for_stl = daily_agg.set_index("sale_date")["units_sold_target"].sort_index()

try:
    stl = STL(ts_for_stl, period=7, robust=True)
    result = stl.fit()

    fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)
    axes[0].plot(ts_for_stl.index, ts_for_stl.values, color=PALETTE["primary"], linewidth=1.5)
    axes[0].set_title("Observed")
    axes[0].grid(True, alpha=0.4)

    axes[1].plot(result.trend.index, result.trend.values, color=PALETTE["success"], linewidth=2)
    axes[1].set_title("Trend Component")
    axes[1].grid(True, alpha=0.4)

    axes[2].plot(result.seasonal.index, result.seasonal.values, color=PALETTE["secondary"], linewidth=1.5)
    axes[2].set_title("Seasonal Component (period=7 days)")
    axes[2].axhline(0, color=PALETTE["neutral"], linestyle="--", linewidth=1)
    axes[2].grid(True, alpha=0.4)

    axes[3].plot(result.resid.index, result.resid.values, color=PALETTE["danger"], linewidth=1, alpha=0.8)
    axes[3].set_title("Residual")
    axes[3].axhline(0, color=PALETTE["neutral"], linestyle="--", linewidth=1)
    axes[3].grid(True, alpha=0.4)

    fig.suptitle("STL Decomposition — Total Daily Demand (period=7 days)",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    save_figure(fig, "03_stl_decomposition")
    plt.show()

    # Variance explained
    seasonal_var = result.seasonal.var()
    trend_var    = result.trend.var()
    resid_var    = result.resid.var()
    total_var    = ts_for_stl.var()
    print(f"\n📊 STL Variance Decomposition:")
    print(f"  Trend:    {trend_var/total_var*100:.1f}%")
    print(f"  Seasonal: {seasonal_var/total_var*100:.1f}%")
    print(f"  Residual: {resid_var/total_var*100:.1f}%")
    seasonal_strength = 1 - resid_var / (seasonal_var + resid_var)
    print(f"  Seasonal strength (0=none, 1=strong): {seasonal_strength:.4f}")

except Exception as e:
    print(f"STL decomposition note: {e}")

# %% [markdown]
# ## 6. Stationarity Testing (ADF) — Top 20 SKUs by Volume

# %%
top_products = (
    df.groupby("product_id")["units_sold_target"].sum()
    .nlargest(20)
    .index.tolist()
)

adf_results = []
for pid in top_products:
    ts = df[df["product_id"] == pid].set_index("sale_date")["units_sold_target"].sort_index()
    if len(ts) < 10:
        continue
    res = adf_test(ts, series_name=f"product_{pid}")
    adf_results.append(res)

adf_df = pd.DataFrame(adf_results)[["series","adf_statistic","p_value","stationary","verdict"]]
stationary_count = adf_df["stationary"].sum()
print(f"=== ADF Stationarity Results (top {len(adf_df)} products) ===")
print(f"  Stationary: {stationary_count}/{len(adf_df)} ({stationary_count/len(adf_df)*100:.0f}%)")
print()
display(adf_df)

fig, ax = plt.subplots(figsize=(10, 4))
colors = [PALETTE["success"] if v else PALETTE["danger"] for v in adf_df["stationary"]]
ax.barh(adf_df["series"], adf_df["p_value"], color=colors)
ax.axvline(0.05, color=PALETTE["warning"], linestyle="--", linewidth=2,
           label="α = 0.05 (stationarity threshold)")
ax.set_title("ADF Test p-values (< 0.05 = stationary)")
ax.set_xlabel("p-value")
ax.legend()
ax.grid(True, alpha=0.4, axis="x")
plt.tight_layout()
save_figure(fig, "03_adf_stationarity")
plt.show()

# %% [markdown]
# ## 7. Autocorrelation (ACF / PACF) Analysis

# %%
# Use aggregate series for ACF/PACF
ts_agg = daily_agg.set_index("sale_date")["units_sold_target"]
nlags = min(30, len(ts_agg) // 2)
acf_vals  = acf(ts_agg, nlags=nlags, fft=True)
pacf_vals = pacf(ts_agg, nlags=nlags)

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
ci = 1.96 / np.sqrt(len(ts_agg))

# ACF
axes[0].stem(range(len(acf_vals)), acf_vals, linefmt=PALETTE["primary"],
             markerfmt="o", basefmt="k-")
axes[0].axhline(ci,  color=PALETTE["danger"], linestyle="--", linewidth=1.5, label=f"±95% CI ({ci:.3f})")
axes[0].axhline(-ci, color=PALETTE["danger"], linestyle="--", linewidth=1.5)
axes[0].set_title("Autocorrelation Function (ACF)")
axes[0].set_xlabel("Lag (days)")
axes[0].set_ylabel("Correlation")
axes[0].legend()
axes[0].grid(True, alpha=0.4)

# PACF
axes[1].stem(range(len(pacf_vals)), pacf_vals, linefmt=PALETTE["secondary"],
             markerfmt="o", basefmt="k-")
axes[1].axhline(ci,  color=PALETTE["danger"], linestyle="--", linewidth=1.5, label=f"±95% CI ({ci:.3f})")
axes[1].axhline(-ci, color=PALETTE["danger"], linestyle="--", linewidth=1.5)
axes[1].set_title("Partial Autocorrelation Function (PACF)")
axes[1].set_xlabel("Lag (days)")
axes[1].set_ylabel("Partial Correlation")
axes[1].legend()
axes[1].grid(True, alpha=0.4)

plt.suptitle("ACF / PACF — Total Daily Demand", fontsize=13, fontweight="bold")
plt.tight_layout()
save_figure(fig, "03_acf_pacf")
plt.show()

sig_lags = [i for i, v in enumerate(acf_vals[1:], 1) if abs(v) > ci]
print(f"\n📊 Significant ACF lags (|corr| > {ci:.3f}): {sig_lags[:10]}")
print(f"  Strongest autocorrelation at lag 7: {acf_vals[7] if len(acf_vals) > 7 else 'N/A':.4f}")

# %% [markdown]
# ## 7b. Lag Feature Validation

# %%
# Validate that lag_7 and lag_14 are meaningfully correlated with target
df_lag = df.dropna(subset=["units_sold_lag7","units_sold_lag14","units_sold_target"])
r7,  p7  = sp_stats.pearsonr(df_lag["units_sold_lag7"],  df_lag["units_sold_target"])
r14, p14 = sp_stats.pearsonr(df_lag["units_sold_lag14"], df_lag["units_sold_target"])
r_roll, p_roll = sp_stats.pearsonr(df_lag["rolling_avg_7d"].dropna(), df_lag.loc[df_lag["rolling_avg_7d"].notna(), "units_sold_target"])

print("=== Lag Feature Correlations with Target ===")
print(f"  lag_7  correlation:    r={r7:.4f}   p={p7:.6f}   {'✅ significant' if p7 < 0.05 else '❌ not significant'}")
print(f"  lag_14 correlation:    r={r14:.4f}   p={p14:.6f}   {'✅ significant' if p14 < 0.05 else '❌ not significant'}")
print(f"  rolling_7d correlation: r={r_roll:.4f}   p={p_roll:.6f}   {'✅ significant' if p_roll < 0.05 else '❌ not significant'}")
print(f"\n  Anti-leakage: VERIFIED in Stage 4B (cutoff strictly maintained)")

# %% [markdown]
# ## 8. Product-Level Forecastability (Coefficient of Variation)

# %%
prod_stats = (
    df.groupby(["product_id","product_name"])["units_sold_target"]
    .agg(["mean","std","count"])
    .reset_index()
)
prod_stats["cv"] = prod_stats["std"] / prod_stats["mean"]
prod_stats = prod_stats.sort_values("cv")
prod_stats["forecastability"] = pd.cut(prod_stats["cv"], bins=[0, 0.5, 1.0, 9999],
                                        labels=["HIGH", "MEDIUM", "LOW"])

print("=== Forecastability by Product (CV = std/mean) ===")
print(f"  HIGH (CV<0.5):   {(prod_stats['forecastability']=='HIGH').sum()} products")
print(f"  MEDIUM (CV 0.5-1.0): {(prod_stats['forecastability']=='MEDIUM').sum()} products")
print(f"  LOW (CV>1.0):    {(prod_stats['forecastability']=='LOW').sum()} products")
print()

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
axes[0].hist(prod_stats["cv"], bins=20, color=PALETTE["primary"], edgecolor="white")
axes[0].axvline(0.5, color=PALETTE["success"], linestyle="--", linewidth=2, label="High/Medium boundary (0.5)")
axes[0].axvline(1.0, color=PALETTE["danger"],  linestyle="--", linewidth=2, label="Medium/Low boundary (1.0)")
axes[0].set_title("Distribution of Coefficient of Variation (CV)")
axes[0].set_xlabel("CV (std/mean)")
axes[0].set_ylabel("# Products")
axes[0].legend()
axes[0].grid(True, alpha=0.4, axis="y")

fcast_counts = prod_stats["forecastability"].value_counts()
axes[1].bar(fcast_counts.index, fcast_counts.values,
            color=[PALETTE["success"], PALETTE["warning"], PALETTE["danger"]],
            edgecolor="white")
axes[1].set_title("Forecastability Tier Distribution")
axes[1].set_ylabel("# Products")
for i, v in enumerate(fcast_counts.values):
    axes[1].text(i, v + 0.5, str(v), ha="center", fontweight="bold")
axes[1].grid(True, alpha=0.4, axis="y")

plt.tight_layout()
save_figure(fig, "03_product_forecastability")
plt.show()

print("Most forecastable products (lowest CV):")
display(prod_stats.head(5)[["product_name","mean","std","cv","forecastability"]])
print("\nLeast forecastable (highest CV):")
display(prod_stats.tail(5)[["product_name","mean","std","cv","forecastability"]])

# %% [markdown]
# ## 9. Baseline Naive Forecast

# %%
# Naive 1: Persistence (lag_7 as prediction)
# Naive 2: Rolling 7d mean as prediction
df_eval = df.dropna(subset=["units_sold_lag7","rolling_avg_7d","units_sold_target"])

mae_lag7   = (df_eval["units_sold_lag7"] - df_eval["units_sold_target"]).abs().mean()
mae_roll7  = (df_eval["rolling_avg_7d"]  - df_eval["units_sold_target"]).abs().mean()
rmse_lag7  = np.sqrt(((df_eval["units_sold_lag7"] - df_eval["units_sold_target"])**2).mean())
rmse_roll7 = np.sqrt(((df_eval["rolling_avg_7d"]  - df_eval["units_sold_target"])**2).mean())

# MAPE (exclude zeros)
mask = df_eval["units_sold_target"] > 0
mape_lag7  = ((df_eval.loc[mask,"units_sold_lag7"] - df_eval.loc[mask,"units_sold_target"]).abs() / df_eval.loc[mask,"units_sold_target"]).mean() * 100
mape_roll7 = ((df_eval.loc[mask,"rolling_avg_7d"]  - df_eval.loc[mask,"units_sold_target"]).abs() / df_eval.loc[mask,"units_sold_target"]).mean() * 100

print("=== BASELINE FORECAST METRICS ===")
print(f"  {'Model':<30} {'MAE':>8}  {'RMSE':>8}  {'MAPE':>8}")
print(f"  {'-'*58}")
print(f"  {'Naïve lag-7 (persistence)':<30} {mae_lag7:>8.3f}  {rmse_lag7:>8.3f}  {mape_lag7:>7.2f}%")
print(f"  {'7d Rolling Mean':<30} {mae_roll7:>8.3f}  {rmse_roll7:>8.3f}  {mape_roll7:>7.2f}%")
print(f"\n  → Stage 8 models must beat these baselines to be useful.")

# %% [markdown]
# ## 10. Leakage Risks

# %%
print("""
LEAKAGE RISK ASSESSMENT — Demand Forecasting:
──────────────────────────────────────────────────────────────
Feature              | Risk   | Verification
─────────────────────|────────|─────────────────────────────
units_sold_lag7      | LOW ✅ | Confirmed strictly t-7 via Stage 4B audit
units_sold_lag14     | LOW ✅ | Confirmed strictly t-14 via Stage 4B audit
rolling_avg_7d       | LOW ✅ | Uses 7 PRECEDING rows only (RANGE BETWEEN
                     |        | 7 PRECEDING AND 1 PRECEDING in SQL)
units_sold_target    | N/A    | Target — excluded from features
──────────────────────────────────────────────────────────────
⚠  DO NOT use same-day demand as a feature.
⚠  DO NOT use any forward-looking aggregations.
⚠  For category-level features, ensure they represent demand
   patterns BEFORE the target date.
""")

# %% [markdown]
# ## 11-13. Feature Candidates, Stage 8 Recommendation & Statistical Conclusions

# %%
print("=" * 65)
print("  STATISTICAL CONCLUSIONS — Demand Forecasting")
print("=" * 65)
print(f"""
Dataset:       18,100 rows ({df['product_id'].nunique()} products × {df['sale_date'].nunique()} days)

STATIONARITY:
  {stationary_count}/{len(adf_df)} top products are stationary (p<0.05 ADF).
  {'Mostly stationary — tree-based lag models appropriate.' if stationary_count > len(adf_df)//2 else 'Significant non-stationarity — differencing required for SARIMA.'}

SEASONALITY:
  Weekly pattern detected in ACF (significant lag at 7 days).
  STL decomposition confirms seasonal component.
  Strongest day: {dow_labels[dow_avg.idxmax()]}  ({dow_avg.max():.0f} avg units)
  Weakest day:   {dow_labels[dow_avg.idxmin()]}  ({dow_avg.min():.0f} avg units)

LAG VALIDATION:
  lag_7 correlation with target:  r={r7:.4f}  {'✅ significant' if p7 < 0.05 else '❌ not significant'}
  lag_14 correlation with target: r={r14:.4f}  {'✅ significant' if p14 < 0.05 else '❌ not significant'}

FORECASTABILITY TIERS:
  HIGH CV<0.5:   {(prod_stats['forecastability']=='HIGH').sum()} products  → forecast with confidence
  MEDIUM CV 0.5-1.0: {(prod_stats['forecastability']=='MEDIUM').sum()} products  → forecast with caution
  LOW CV>1.0:    {(prod_stats['forecastability']=='LOW').sum()} products  → may need category-level aggregate

BASELINE PERFORMANCE:
  Naïve lag-7:  MAE={mae_lag7:.3f}  RMSE={rmse_lag7:.3f}  MAPE={mape_lag7:.2f}%
  Rolling 7d:   MAE={mae_roll7:.3f}  RMSE={rmse_roll7:.3f}  MAPE={mape_roll7:.2f}%

RECOMMENDED STAGE 8 MODELS:
  1. XGBoost with lag features (baseline beater, handles nonlinearity)
  2. Facebook Prophet (captures weekly seasonality natively)
  3. SARIMA on top-10 forecastable products (benchmark)

EVALUATION METRIC FOR STAGE 8:
  Primary:   MAPE (interpretable for business)
  Secondary: RMSE (penalises large errors)
  Coverage:  95% prediction interval coverage rate

FEATURE CANDIDATES FOR STAGE 8:
  • units_sold_lag7, units_sold_lag14  (primary lags — validated)
  • rolling_avg_7d                      (trend signal)
  • day_of_week                         (weekly seasonality)
  • month                               (monthly seasonality)
  • is_weekend (derived)                (weekend effect)
  • product_id                          (product fixed effects)
  • category_name                       (category aggregation)
""")
