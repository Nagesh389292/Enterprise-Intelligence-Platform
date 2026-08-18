"""
data_science/agents/inventory_agent.py
========================================
Stage 10 — InventoryAgent

Consumes stockout predictions (analytics.fact_predictions_inventory_stockout)
and demand forecasts (analytics.fact_predictions_sku_demand) to produce
REORDER_INVENTORY decisions.

Reorder quantity formula:
    demand_7d = sum of predicted_demand_units over next 7 days (per SKU)
    gap       = max(0, demand_7d × SAFETY_FACTOR - quantity_available)
    reorder   = min(gap, max_reorder_cap)

The CriticAgent will challenge reorder_qty > 2 × demand_7d downstream.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

import numpy as np
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

# Thresholds & caps
CRITICAL_STOCKOUT_PROB = 0.75
HIGH_STOCKOUT_PROB     = 0.50
SAFETY_FACTOR          = 1.25         # buffer above pure demand forecast
MAX_REORDER_CAP        = 2000         # hard ceiling on any single reorder
MIN_REORDER_QTY        = 1


class InventoryAgent(BaseAgent):
    """
    Analyses stockout and demand predictions to recommend reorder actions.
    Reads from analytics.fact_predictions_inventory_stockout,
    analytics.fact_predictions_sku_demand, and
    analytics.ml_inventory_stockout_features for business context.
    """

    agent_name = "InventoryAgent"
    domain     = "inventory"
    version    = "1.0.0"

    def __init__(self, db_engine=None):
        super().__init__()
        self.engine = db_engine or get_engine()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_contexts(self) -> List[AgentContext]:
        """
        Join stockout predictions with demand forecasts and inventory business
        context. Returns one AgentContext per SKU at or above HIGH_STOCKOUT_PROB.
        """
        stockout_query = text("""
            WITH latest_stockout AS (
                SELECT DISTINCT ON (item_id)
                    item_id,
                    stockout_risk_prob_7d,
                    stockout_alert_flag_7d,
                    risk_severity,
                    model_version,
                    run_id::text AS pred_run_id
                FROM analytics.fact_predictions_inventory_stockout
                ORDER BY item_id, prediction_timestamp DESC
            )
            SELECT
                ls.item_id,
                ls.stockout_risk_prob_7d,
                ls.stockout_alert_flag_7d,
                ls.risk_severity,
                ls.model_version,
                COALESCE(inv.reorder_quantity, 100)    AS reorder_quantity_default,
                COALESCE(inv.quantity_available, 0)    AS quantity_available,
                COALESCE(inv.reorder_point, 50)        AS reorder_point,
                COALESCE(inv.unit_cost, 0.0)           AS unit_cost,
                COALESCE(inv.product_name, 'Unknown')  AS supplier_name,
                inv.product_id                         AS product_uuid
            FROM latest_stockout ls
            LEFT JOIN analytics.ml_inventory_stockout_risk inv
                   ON ls.item_id::integer = inv.inventory_id
            WHERE ls.stockout_risk_prob_7d >= :min_prob
            ORDER BY ls.stockout_risk_prob_7d DESC
        """)

        demand_query = text("""
            SELECT
                product_id::text AS product_id,
                SUM(predicted_demand_units) AS demand_7d_total,
                AVG(lower_bound_95)         AS lower_95,
                AVG(upper_bound_95)         AS upper_95
            FROM analytics.fact_predictions_sku_demand
            WHERE forecast_date >= (SELECT MAX(forecast_date) - INTERVAL '6 days' FROM analytics.fact_predictions_sku_demand)
              AND forecast_date <= (SELECT MAX(forecast_date) FROM analytics.fact_predictions_sku_demand)
            GROUP BY product_id
        """)

        try:
            df_stockout = pd.read_sql(
                stockout_query, self.engine,
                params={"min_prob": HIGH_STOCKOUT_PROB}
            )
            df_demand = pd.read_sql(demand_query, self.engine)
        except Exception as exc:
            logger.warning("InventoryAgent: DB query failed (%s). Returning empty.", exc)
            return []

        if df_stockout.empty:
            logger.info("InventoryAgent: No SKUs above stockout threshold.")
            return []

        # Merge demand onto stockout predictions using product_uuid from inventory join
        # item_id (int) → product_uuid (UUID) → matches product_id in demand predictions
        df = df_stockout.merge(
            df_demand,
            left_on="product_uuid",
            right_on="product_id",
            how="left"
        )
        df["demand_7d_total"] = df["demand_7d_total"].fillna(
            df["reorder_quantity_default"]   # fallback if no demand forecast
        )

        run_id = uuid.uuid4()
        contexts = []
        for _, row in df.iterrows():
            ctx = AgentContext(
                domain=Domain.INVENTORY,
                entity_id=str(row["item_id"]),
                predictions={
                    "stockout_risk_prob_7d":  float(row["stockout_risk_prob_7d"]),
                    "stockout_alert_flag_7d": int(row["stockout_alert_flag_7d"]),
                    "risk_severity":          str(row["risk_severity"]),
                    "model_version":          str(row["model_version"]),
                },
                business_ctx={
                    "demand_7d":               float(row["demand_7d_total"]),
                    "quantity_available":       float(row["quantity_available"]),
                    "reorder_point":            float(row["reorder_point"]),
                    "reorder_quantity_default": float(row["reorder_quantity_default"]),
                    "unit_cost":                float(row["unit_cost"]),
                    "supplier_name":            str(row["supplier_name"]),
                },
                run_id=run_id,
            )
            contexts.append(ctx)

        logger.info("InventoryAgent: Loaded %d actionable SKU contexts.", len(contexts))
        return contexts

    # ------------------------------------------------------------------
    # Core reasoning
    # ------------------------------------------------------------------

    def analyze(self, context: AgentContext) -> AgentOutput:
        """Compute reorder quantity and produce REORDER_INVENTORY recommendation."""
        preds = context.predictions
        bctx  = context.business_ctx

        stockout_prob  = preds["stockout_risk_prob_7d"]
        risk_severity  = preds["risk_severity"]
        demand_7d      = bctx.get("demand_7d", 0.0)
        qty_available  = bctx.get("quantity_available", 0.0)
        reorder_point  = bctx.get("reorder_point", 50.0)
        unit_cost      = bctx.get("unit_cost", 0.0)
        supplier       = bctx.get("supplier_name", "Unknown")

        reasoning: List[str] = []
        reasoning.append(
            f"Stockout risk: {stockout_prob:.1%} over 7 days (severity={risk_severity})"
        )
        reasoning.append(
            f"Current inventory: {qty_available:.0f} units | Reorder point: {reorder_point:.0f} units"
        )
        reasoning.append(
            f"7-day demand forecast: {demand_7d:.1f} units (Ridge regression champion)"
        )

        # Compute reorder quantity
        gap = max(0.0, demand_7d * SAFETY_FACTOR - qty_available)
        raw_reorder = round(gap)

        # Apply cap
        reorder_qty = max(MIN_REORDER_QTY, min(raw_reorder, MAX_REORDER_CAP)) if raw_reorder > 0 else 0

        reasoning.append(
            f"Reorder formula: max(0, demand_7d({demand_7d:.1f}) × safety({SAFETY_FACTOR}) - "
            f"qty_avail({qty_available:.0f})) = {gap:.1f} → rounded to {raw_reorder}"
        )

        if reorder_qty == 0:
            action = (
                f"No reorder needed for {context.entity_id}: "
                f"available inventory ({qty_available:.0f}) covers 7-day demand with safety buffer."
            )
            confidence = 1.0 - stockout_prob
            reasoning.append("Available stock sufficient — no reorder action required.")
        else:
            estimated_cost = reorder_qty * unit_cost if unit_cost > 0 else None
            cost_str = f" (est. cost: £{estimated_cost:,.0f})" if estimated_cost else ""
            action = (
                f"REORDER {reorder_qty} units of {context.entity_id} "
                f"from {supplier}{cost_str}."
            )
            confidence = stockout_prob * 0.90
            reasoning.append(
                f"Reorder {reorder_qty} units from '{supplier}'{cost_str}."
            )

        if stockout_prob >= CRITICAL_STOCKOUT_PROB:
            reasoning.append(
                f"⚠ CRITICAL stockout risk ({stockout_prob:.1%}) — expedite reorder."
            )

        return AgentOutput(
            agent_name="InventoryAgent",
            domain=Domain.INVENTORY,
            decision_type=DecisionType.REORDER_INVENTORY,
            entity_id=context.entity_id,
            recommended_action=action,
            quantity=float(reorder_qty),
            urgency_hours=None,
            confidence=round(min(confidence, 1.0), 4),
            reasoning_steps=reasoning,
            evidence={
                "stockout_risk_prob_7d": stockout_prob,
                "risk_severity":         risk_severity,
                "demand_7d":             demand_7d,
                "quantity_available":    qty_available,
                "reorder_point":         reorder_point,
                "computed_reorder_qty":  reorder_qty,
                "unit_cost":             unit_cost,
                "supplier":              supplier,
            },
            source_models=["stockout_xgboost", "demand_ridge"],
            run_id=context.run_id,
        )
