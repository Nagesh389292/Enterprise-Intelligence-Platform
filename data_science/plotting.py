"""
data_science/plotting.py
------------------------
Reusable chart helpers for all Stage 7 notebooks.
All charts follow the NexaCore brand palette and export
to docs/data_science/figures/ automatically.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from data_science.config import (
    PALETTE, CATEGORICAL_PALETTE, SEQUENTIAL_PALETTE,
    FIGURES_DIR, FIGURE_DPI, FIGURE_FORMAT,
)

# ---------------------------------------------------------------------------
# Matplotlib global style
# ---------------------------------------------------------------------------

plt.rcParams.update({
    "figure.facecolor":    PALETTE["background"],
    "axes.facecolor":      PALETTE["background"],
    "axes.edgecolor":      PALETTE["neutral"],
    "axes.labelcolor":     PALETTE["text"],
    "text.color":          PALETTE["text"],
    "xtick.color":         PALETTE["neutral"],
    "ytick.color":         PALETTE["neutral"],
    "grid.color":          "#DEE2E6",
    "grid.linestyle":      "--",
    "grid.alpha":          0.6,
    "font.family":         "DejaVu Sans",
    "font.size":           11,
    "axes.titlesize":      13,
    "axes.titleweight":    "bold",
    "figure.dpi":          100,
})


# ---------------------------------------------------------------------------
# Export helper
# ---------------------------------------------------------------------------

def save_figure(fig: plt.Figure, name: str) -> str:
    """Save figure to docs/data_science/figures/. Returns file path."""
    path = os.path.join(FIGURES_DIR, f"{name}.{FIGURE_FORMAT}")
    fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight",
                facecolor=PALETTE["background"])
    print(f"  [saved] {path}")
    return path


# ---------------------------------------------------------------------------
# 1. Distribution comparison (two groups)
# ---------------------------------------------------------------------------

def plot_distribution_comparison(
    data: pd.DataFrame,
    value_col: str,
    group_col: str,
    title: str,
    xlabel: str = "",
    figname: str | None = None,
    figsize: tuple = (12, 4),
) -> plt.Figure:
    """Histogram + KDE for a continuous variable split by a binary group."""
    import seaborn as sns
    fig, axes = plt.subplots(1, 2, figsize=figsize)

    groups = data[group_col].unique()
    colors = [PALETTE["primary"], PALETTE["danger"]]

    # Histogram
    for g, c in zip(groups, colors):
        subset = data.loc[data[group_col] == g, value_col].dropna()
        axes[0].hist(subset, bins=30, alpha=0.6, color=c, label=str(g),
                     edgecolor="white", linewidth=0.5)
    axes[0].set_title(f"{xlabel} — Histogram")
    axes[0].set_xlabel(xlabel or value_col)
    axes[0].legend()
    axes[0].grid(True, alpha=0.4)

    # KDE
    for g, c in zip(groups, colors):
        subset = data.loc[data[group_col] == g, value_col].dropna()
        subset.plot.kde(ax=axes[1], color=c, label=str(g), linewidth=2)
    axes[1].set_title(f"{xlabel} — Density")
    axes[1].set_xlabel(xlabel or value_col)
    axes[1].legend()
    axes[1].grid(True, alpha=0.4)

    fig.suptitle(title, fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    if figname:
        save_figure(fig, figname)
    return fig


# ---------------------------------------------------------------------------
# 2. Correlation heatmap
# ---------------------------------------------------------------------------

def plot_correlation_heatmap(
    df: pd.DataFrame,
    cols: list[str],
    title: str = "Correlation Matrix",
    figname: str | None = None,
    figsize: tuple = (10, 8),
    method: str = "pearson",
) -> plt.Figure:
    import seaborn as sns
    corr = df[cols].corr(method=method)
    mask = np.triu(np.ones_like(corr, dtype=bool))

    fig, ax = plt.subplots(figsize=figsize)
    sns.heatmap(
        corr, mask=mask, annot=True, fmt=".2f", linewidths=0.5,
        cmap="RdBu_r", vmin=-1, vmax=1, ax=ax,
        annot_kws={"size": 9},
    )
    ax.set_title(title, pad=16)
    fig.tight_layout()
    if figname:
        save_figure(fig, figname)
    return fig


# ---------------------------------------------------------------------------
# 3. Bar chart with value labels
# ---------------------------------------------------------------------------

def plot_bar(
    labels: list,
    values: list,
    title: str,
    xlabel: str = "",
    ylabel: str = "",
    color: str | None = None,
    figname: str | None = None,
    figsize: tuple = (10, 5),
    horizontal: bool = False,
    fmt: str = "{:.0f}",
) -> plt.Figure:
    fig, ax = plt.subplots(figsize=figsize)
    c = color or PALETTE["primary"]

    if horizontal:
        bars = ax.barh(labels, values, color=c, edgecolor="white", linewidth=0.5)
        for bar in bars:
            w = bar.get_width()
            ax.text(w * 1.01, bar.get_y() + bar.get_height() / 2,
                    fmt.format(w), va="center", ha="left", fontsize=9)
        ax.set_xlabel(ylabel)
        ax.set_ylabel(xlabel)
        ax.invert_yaxis()
    else:
        bars = ax.bar(labels, values, color=c, edgecolor="white", linewidth=0.5)
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h * 1.01,
                    fmt.format(h), ha="center", va="bottom", fontsize=9)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        plt.xticks(rotation=45, ha="right")

    ax.set_title(title)
    ax.grid(True, alpha=0.4, axis="x" if horizontal else "y")
    fig.tight_layout()
    if figname:
        save_figure(fig, figname)
    return fig


# ---------------------------------------------------------------------------
# 4. Time-series line chart
# ---------------------------------------------------------------------------

def plot_time_series(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    title: str,
    ylabel: str = "",
    resample: str | None = "ME",
    agg: str = "sum",
    figname: str | None = None,
    figsize: tuple = (14, 5),
) -> plt.Figure:
    ts = df.set_index(date_col)[value_col].sort_index()
    if resample:
        ts = ts.resample(resample).agg(agg)

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(ts.index, ts.values, color=PALETTE["primary"], linewidth=2)
    ax.fill_between(ts.index, ts.values, alpha=0.1, color=PALETTE["primary"])
    ax.set_title(title)
    ax.set_ylabel(ylabel or value_col)
    ax.grid(True, alpha=0.4)
    fig.autofmt_xdate()
    fig.tight_layout()
    if figname:
        save_figure(fig, figname)
    return fig


# ---------------------------------------------------------------------------
# 5. Box plots by group
# ---------------------------------------------------------------------------

def plot_boxplot_by_group(
    data: pd.DataFrame,
    value_col: str,
    group_col: str,
    title: str,
    ylabel: str = "",
    figname: str | None = None,
    figsize: tuple = (10, 5),
) -> plt.Figure:
    import seaborn as sns
    fig, ax = plt.subplots(figsize=figsize)
    sns.boxplot(
        data=data, x=group_col, y=value_col, ax=ax,
        palette=CATEGORICAL_PALETTE[:data[group_col].nunique()],
        linewidth=1.2,
    )
    ax.set_title(title)
    ax.set_ylabel(ylabel or value_col)
    ax.grid(True, alpha=0.4, axis="y")
    fig.tight_layout()
    if figname:
        save_figure(fig, figname)
    return fig


# ---------------------------------------------------------------------------
# 6. Lorenz curve (for concentration / Gini)
# ---------------------------------------------------------------------------

def plot_lorenz_curve(
    values: pd.Series,
    title: str = "Lorenz Curve",
    figname: str | None = None,
    figsize: tuple = (7, 6),
) -> tuple[plt.Figure, float]:
    sorted_vals = np.sort(values.dropna().values)
    cumulative  = np.cumsum(sorted_vals) / sorted_vals.sum()
    lorenz_x    = np.linspace(0, 1, len(cumulative))

    from scipy.integrate import trapezoid
    gini = 1 - 2 * trapezoid(cumulative, lorenz_x)

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(lorenz_x, lorenz_x, color=PALETTE["neutral"],
            linestyle="--", label="Perfect equality", linewidth=1.5)
    ax.plot(lorenz_x, cumulative, color=PALETTE["primary"],
            linewidth=2.5, label=f"Lorenz curve (Gini={gini:.3f})")
    ax.fill_between(lorenz_x, lorenz_x, cumulative,
                    alpha=0.15, color=PALETTE["primary"])
    ax.set_xlabel("Cumulative share of customers")
    ax.set_ylabel("Cumulative share of revenue")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.4)
    fig.tight_layout()
    if figname:
        save_figure(fig, figname)
    return fig, gini


# ---------------------------------------------------------------------------
# 7. Feature importance bar (horizontal)
# ---------------------------------------------------------------------------

def plot_feature_importance(
    importance_df: pd.DataFrame,
    feature_col: str = "feature",
    value_col: str = "mutual_information",
    title: str = "Feature Importance",
    top_n: int = 15,
    figname: str | None = None,
    figsize: tuple = (10, 6),
) -> plt.Figure:
    top = importance_df.nlargest(top_n, value_col)
    colors = [PALETTE["primary"]] * len(top)
    colors[0] = PALETTE["success"]

    fig, ax = plt.subplots(figsize=figsize)
    ax.barh(top[feature_col][::-1], top[value_col][::-1],
            color=colors[::-1], edgecolor="white", linewidth=0.5)
    ax.set_title(title)
    ax.set_xlabel(value_col.replace("_", " ").title())
    ax.grid(True, alpha=0.4, axis="x")
    fig.tight_layout()
    if figname:
        save_figure(fig, figname)
    return fig


# ---------------------------------------------------------------------------
# 8. Scatter plot with colour encoding
# ---------------------------------------------------------------------------

def plot_scatter(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    hue_col: str | None = None,
    title: str = "",
    figname: str | None = None,
    figsize: tuple = (9, 6),
    alpha: float = 0.5,
) -> plt.Figure:
    import seaborn as sns
    fig, ax = plt.subplots(figsize=figsize)
    if hue_col:
        sns.scatterplot(data=df, x=x_col, y=y_col, hue=hue_col,
                        alpha=alpha, ax=ax, palette=CATEGORICAL_PALETTE)
    else:
        ax.scatter(df[x_col], df[y_col], color=PALETTE["primary"],
                   alpha=alpha, edgecolors="white", linewidths=0.3)
    ax.set_title(title)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.grid(True, alpha=0.4)
    fig.tight_layout()
    if figname:
        save_figure(fig, figname)
    return fig


# ---------------------------------------------------------------------------
# 9. Cohort heatmap
# ---------------------------------------------------------------------------

def plot_cohort_heatmap(
    pivot: pd.DataFrame,
    title: str = "Cohort Heatmap",
    fmt: str = ".1%",
    figname: str | None = None,
    figsize: tuple = (14, 6),
) -> plt.Figure:
    import seaborn as sns
    fig, ax = plt.subplots(figsize=figsize)
    sns.heatmap(
        pivot, annot=True, fmt=fmt, linewidths=0.5,
        cmap=SEQUENTIAL_PALETTE, ax=ax,
        annot_kws={"size": 8},
    )
    ax.set_title(title, pad=16)
    fig.tight_layout()
    if figname:
        save_figure(fig, figname)
    return fig
