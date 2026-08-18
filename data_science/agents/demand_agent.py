"""
data_science/agents/demand_agent.py
=====================================
Stage 10 — DemandAgent

Consumes SKU demand forecasts (analytics.fact_predictions_sku_demand)
and compares them to current inventory from the Gold layer to produce
ADJUST_DEMAND_PLAN decisions.

Directions:
  INCREASE_STOCK_ORDER  — demand_7d > qty_available × 0.85
  REDUCE_PURCHASE_ORDER — demand_7d < qty_available × 0.40
  RUN_PROMOTION         — demand_7d < qty_available × 0.40 AND days_of_supply > 30
  MAINTAIN              — balanced demand / supply
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy import text

from data_science.db import get_engine
from data_science.agents.base import BaseAgent
from data_science.agents.schemas import (
    AgentContext,
    AgentOutput,
    Domain,
    DecisionType,
)

logger = logging.getLogger(__name__)

# Thresholds
DEMAND_SUPPLY_HIGH = 0.85    # demand_7d > qty_available × this → increase order
DEMAND_SUPPLY_LOW  = 0.40    # demand_7d < qty_available × this → reduce / promote
EXCESS_DOS_DAYS    = 30      # days-of-supply above this triggers promotion


class DemandAgent(BaseAgent):
    """
    Analyses SKU demand forecasts against current inventory levels to
    produce demand plan adjustment recommendations.
    """

    agent_name = "DemandAgent"
    domain     = "demand"
    version    = "1.0.0"

    def __init__(self, db_engine=None):
        super().__init__()
        self.engine = db_engine or get_engine()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_contexts(self) -> List[AgentContext]:
        """
        Load 7-day demand forecasts per SKU, join with current inventory
        Gold table, and return one AgentContext per SKU where action is needed.
        """
        query = text("""
            WITH max_date AS (
                SELECT MAX(forecast_date) AS latest FROM analytics.fact_predictions_sku_demand
            ),
            demand_7d AS (
                SELECT
                    product_id::text AS product_id,
                    SUM(predicted_demand_units)  AS demand_7d,
                    AVG(lower_bound_95)          AS lower_95,
                    AVG(upper_bound_95)          AS upper_95,
                    COUNT(*)                     AS forecast_days
                FROM analytics.fact_predictions_sku_demand, max_date
                WHERE forecast_date >= max_date.latest - INTERVAL '6 days'
                  AND forecast_date <= max_date.latest
                GROUP BY product_id
            )
            SELECT
                d.product_id,
                d.demand_7d,
                d.lower_95,
                d.upper_95,
                d.forecast_days,
                COALESCE(inv.quantity_available, 0)     AS quantity_available,
                COALESCE(inv.reorder_point, 50)         AS reorder_point,
                COALESCE(inv.days_of_supply, 0)         AS days_of_supply,
                COALESCE(inv.unit_price, 0.0)           AS unit_price,
                COALESCE(inv.product_name, 'Unknown')   AS supplier_name
            FROM demand_7d d
            LEFT JOIN analytics.ml_inventory_stockout_risk inv
                   ON d.product_id = inv.product_id::text
            WHERE d.demand_7d IS NOT NULL
            ORDER BY d.demand_7d DESC
        """)

        try:
            df = pd.read_sql(query, self.engine)
        except Exception as exc:
            logger.warning("DemandAgent: DB query failed (%s). Returning empty.", exc)
            return []

        if df.empty:
            logger.info("DemandAgent: No demand forecasts found.")
            return []

        run_id = uuid.uuid4()
        contexts = []
        for _, row in df.iterrows():
            ctx = AgentContext(
                domain=Domain.DEMAND,
                entity_id=str(row["product_id"]),
                predictions={
                    "demand_7d":     float(row["demand_7d"]),
                    "lower_95":      float(row["lower_95"]) if row["lower_95"] is not None else None,
                    "upper_95":      float(row["upper_95"]) if row["upper_95"] is not None else None,
                    "forecast_days": int(row["forecast_days"]),
                },
                business_ctx={
                    "quantity_available": float(row["quantity_available"]),
                    "reorder_point":      float(row["reorder_point"]),
                    "days_of_supply":     float(row["days_of_supply"]),
                    "unit_price":         float(row["unit_price"]),
                    "supplier_name":      str(row["supplier_name"]),
                },
                run_id=run_id,
            )
            contexts.append(ctx)

        logger.info("DemandAgent: Loaded %d SKU demand contexts.", len(contexts))
        return contexts

    # ------------------------------------------------------------------
    # Core reasoning
    # ------------------------------------------------------------------

    def analyze(self, context: AgentContext) -> AgentOutput:
        """Compare demand to inventory and recommend demand plan adjustment."""
        preds = context.predictions
        bctx  = context.business_ctx

        demand_7d   = preds["demand_7d"]
        lower_95    = preds.get("lower_95") or demand_7d * 0.85
        upper_95    = preds.get("upper_95") or demand_7d * 1.15
        qty_avail   = bctx.get("quantity_available", 0.0)
        dos         = bctx.get("days_of_supply", 0.0)
        unit_price  = bctx.get("unit_price", 0.0)
        supplier    = bctx.get("supplier_name", "Unknown")

        reasoning: List[str] = []
        reasoning.append(
            f"7-day demand forecast: {demand_7d:.1f} units "
            f"(95% CI: [{lower_95:.1f}, {upper_95:.1f}])"
        )
        reasoning.append(
            f"Current inventory: {qty_avail:.0f} units | Days-of-supply: {dos:.1f} days"
        )

        # Direction logic
        supply_ratio = demand_7d / qty_avail if qty_avail > 0 else float("inf")
        reasoning.append(
            f"Demand/Supply ratio: {supply_ratio:.2f} "
            f"(thresholds: high={DEMAND_SUPPLY_HIGH}, low={DEMAND_SUPPLY_LOW})"
        )

        if supply_ratio >= DEMAND_SUPPLY_HIGH:
            direction  = "INCREASE_STOCK_ORDER"
            magnitude  = round(demand_7d - qty_avail * DEMAND_SUPPLY_HIGH, 1)
            action = (
                f"INCREASE STOCK ORDER for {context.entity_id}: "
                f"demand ({demand_7d:.0f} units) approaching inventory ({qty_avail:.0f} units). "
                f"Recommend ordering {magnitude:.0f} additional units from {supplier}."
            )
            confidence = min(supply_ratio / 2.0, 0.95)
            reasoning.append(
                f"Supply insufficient: demand/supply ratio {supply_ratio:.2f} ≥ {DEMAND_SUPPLY_HIGH}. "
                f"Order {magnitude:.0f} additional units."
            )

        elif supply_ratio < DEMAND_SUPPLY_LOW and dos > EXCESS_DOS_DAYS:
            direction  = "RUN_PROMOTION"
            magnitude  = round(qty_avail - demand_7d, 1)
            est_revenue = magnitude * unit_price if unit_price > 0 else None
            rev_str     = f" (potential revenue: £{est_revenue:,.0f})" if est_revenue else ""
            action = (
                f"RUN PROMOTION for {context.entity_id}: excess inventory of "
                f"{magnitude:.0f} units with {dos:.0f} days-of-supply. "
                f"Launch promotional campaign to accelerate sell-through{rev_str}."
            )
            confidence = 0.70
            reasoning.append(
                f"Excess supply: dos={dos:.0f}d > {EXCESS_DOS_DAYS}d AND ratio={supply_ratio:.2f}. "
                "Promotion recommended to clear stock."
            )

        elif supply_ratio < DEMAND_SUPPLY_LOW:
            direction  = "REDUCE_PURCHASE_ORDER"
            magnitude  = round(qty_avail - demand_7d, 1)
            action = (
                f"REDUCE PURCHASE ORDER for {context.entity_id}: "
                f"demand ({demand_7d:.0f} units) well below inventory ({qty_avail:.0f} units). "
                f"Hold excess {magnitude:.0f} units — defer next order."
            )
            confidence = 0.75
            reasoning.append(
                f"Demand low vs supply: ratio={supply_ratio:.2f} < {DEMAND_SUPPLY_LOW}. "
                f"Defer purchase order by ~{dos:.0f} days."
            )

        else:
            direction  = "MAINTAIN"
            magnitude  = 0.0
            action = (
                f"MAINTAIN current purchase plan for {context.entity_id}: "
                f"demand/supply balanced (ratio={supply_ratio:.2f})."
            )
            confidence = 0.80
            reasoning.append(f"Balanced: demand/supply ratio {supply_ratio:.2f} within normal range.")

        return AgentOutput(
            agent_name="DemandAgent",
            domain=Domain.DEMAND,
            decision_type=DecisionType.ADJUST_DEMAND_PLAN,
            entity_id=context.entity_id,
            recommended_action=action,
            quantity=float(magnitude) if magnitude else None,
            urgency_hours=None,
            confidence=round(confidence, 4),
            reasoning_steps=reasoning,
            evidence={
                "demand_7d":       demand_7d,
                "quantity_avail":  qty_avail,
                "supply_ratio":    supply_ratio,
                "days_of_supply":  dos,
                "direction":       direction,
                "magnitude":       magnitude,
            },
            source_models=["demand_ridge"],
            run_id=context.run_id,
        )
