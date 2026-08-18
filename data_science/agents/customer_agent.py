"""
data_science/agents/customer_agent.py
=======================================
Stage 10 — CustomerAgent

Consumes churn predictions from analytics.fact_predictions_customer_churn
and joins Gold dim_customers context to produce RETAIN_CUSTOMER decisions.

Retention tiers:
  P1 (churn_prob >= 0.70 AND high-value) → phone + discount
  P2 (churn_prob >= 0.50)                → email intervention
  MONITOR (churn_prob < 0.50)            → no action
"""

from __future__ import annotations

import logging
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

# Thresholds
HIGH_CHURN_THRESHOLD   = 0.70
MEDIUM_CHURN_THRESHOLD = 0.50
HIGH_VALUE_PERCENTILE  = 0.60   # top 40% by total_spend = high value


class CustomerAgent(BaseAgent):
    """
    Analyses churn predictions to recommend customer retention actions.
    Reads from analytics.fact_predictions_customer_churn and Gold dim_customers.
    """

    agent_name = "CustomerAgent"
    domain     = "customer"
    version    = "1.0.0"

    def __init__(self, db_engine=None):
        super().__init__()
        self.engine = db_engine or get_engine()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_contexts(self) -> List[AgentContext]:
        """
        Load the latest churn predictions joined with customer business context.
        Returns one AgentContext per customer where churn action is warranted
        (churn_prob >= MEDIUM_CHURN_THRESHOLD or high-risk tier).
        """
        query = text("""
            WITH latest_preds AS (
                SELECT DISTINCT ON (customer_id)
                    customer_id,
                    churn_probability,
                    predicted_churn_flag,
                    risk_tier,
                    model_version,
                    run_id::text AS pred_run_id,
                    prediction_timestamp
                FROM analytics.fact_predictions_customer_churn
                ORDER BY customer_id, prediction_timestamp DESC
            )
            SELECT
                lp.customer_id,
                lp.churn_probability,
                lp.predicted_churn_flag,
                lp.risk_tier,
                lp.model_version,
                lp.pred_run_id,
                COALESCE(c.total_orders_to_cutoff, 0)        AS total_orders,
                COALESCE(c.total_spend_to_cutoff, 0.0)        AS total_spend,
                COALESCE(c.account_tenure_days, 0)            AS tenure_days,
                COALESCE(c.avg_csat_score_to_cutoff, 3.0)     AS avg_csat_score
            FROM latest_preds lp
            LEFT JOIN analytics.ml_customer_churn_features c
                   ON lp.customer_id::uuid = c.customer_id
            WHERE lp.churn_probability >= :min_prob
            ORDER BY lp.churn_probability DESC
        """)

        try:
            df = pd.read_sql(
                query,
                self.engine,
                params={"min_prob": MEDIUM_CHURN_THRESHOLD}
            )
        except Exception as exc:
            logger.warning("CustomerAgent: DB query failed (%s). Returning empty context list.", exc)
            return []

        if df.empty:
            logger.info("CustomerAgent: No customers above churn threshold.")
            return []

        # Compute high-value threshold from loaded dataset
        spend_threshold = df["total_spend"].quantile(HIGH_VALUE_PERCENTILE)

        import uuid
        run_id = uuid.uuid4()
        contexts = []
        for _, row in df.iterrows():
            ctx = AgentContext(
                domain=Domain.CUSTOMER,
                entity_id=row["customer_id"],
                predictions={
                    "churn_probability":    float(row["churn_probability"]),
                    "predicted_churn_flag": int(row["predicted_churn_flag"]),
                    "risk_tier":            str(row["risk_tier"]),
                    "model_version":        str(row["model_version"]),
                },
                business_ctx={
                    "total_orders":   int(row["total_orders"]),
                    "total_spend":    float(row["total_spend"]),
                    "tenure_days":    int(row["tenure_days"]),
                    "avg_csat_score": float(row["avg_csat_score"]),
                    "is_high_value":  bool(row["total_spend"] >= spend_threshold),
                },
                run_id=run_id,
            )
            contexts.append(ctx)

        logger.info("CustomerAgent: Loaded %d actionable customer contexts.", len(contexts))
        return contexts

    # ------------------------------------------------------------------
    # Core reasoning
    # ------------------------------------------------------------------

    def analyze(self, context: AgentContext) -> AgentOutput:
        """Apply retention tier logic and produce RETAIN_CUSTOMER recommendation."""
        preds = context.predictions
        bctx  = context.business_ctx

        churn_prob  = preds["churn_probability"]
        is_high_val = bctx.get("is_high_value", False)
        total_spend = bctx.get("total_spend", 0.0)
        tenure_days = bctx.get("tenure_days", 0)
        csat        = bctx.get("avg_csat_score", 3.0)

        reasoning: List[str] = []
        reasoning.append(
            f"Churn probability: {churn_prob:.1%} (risk_tier={preds['risk_tier']})"
        )
        reasoning.append(
            f"Customer value: £{total_spend:,.0f} lifetime spend "
            f"({'HIGH' if is_high_val else 'STANDARD'} value segment)"
        )
        reasoning.append(f"Tenure: {tenure_days} days | CSAT: {csat:.1f}/5.0")

        # --- Tier assignment ---
        if churn_prob >= HIGH_CHURN_THRESHOLD and is_high_val:
            tier       = "P1"
            channel    = "PHONE + DISCOUNT"
            action     = (
                f"PRIORITY-1 retention: call {context.entity_id} within 24h "
                f"and offer targeted discount. Revenue at risk: £{total_spend:,.0f}."
            )
            confidence = churn_prob * 0.90      # high confidence, slight uncertainty from low PR-AUC
            reasoning.append(
                f"P1 trigger: churn_prob {churn_prob:.1%} ≥ {HIGH_CHURN_THRESHOLD:.0%} "
                f"AND high-value customer. Phone + discount channel recommended."
            )

        elif churn_prob >= HIGH_CHURN_THRESHOLD and not is_high_val:
            tier       = "P1_STANDARD"
            channel    = "EMAIL + DISCOUNT"
            action     = (
                f"PRIORITY-1 retention: send personalised discount email to {context.entity_id}. "
                f"Revenue at risk: £{total_spend:,.0f}."
            )
            confidence = churn_prob * 0.85
            reasoning.append(
                f"P1 trigger: churn_prob {churn_prob:.1%} ≥ {HIGH_CHURN_THRESHOLD:.0%} "
                f"(standard value). Email + discount channel recommended."
            )

        elif churn_prob >= MEDIUM_CHURN_THRESHOLD:
            tier       = "P2"
            channel    = "EMAIL"
            action     = (
                f"STANDARD retention: send re-engagement email to {context.entity_id}. "
                f"Revenue at risk: £{total_spend:,.0f}."
            )
            confidence = churn_prob * 0.75
            reasoning.append(
                f"P2 trigger: churn_prob {churn_prob:.1%} in [{MEDIUM_CHURN_THRESHOLD:.0%}, "
                f"{HIGH_CHURN_THRESHOLD:.0%}). Email re-engagement recommended."
            )

        else:
            # Should not be reached given the DB filter, but handle defensively
            tier       = "MONITOR"
            channel    = "NONE"
            action     = f"MONITOR {context.entity_id}: churn probability below action threshold."
            confidence = 0.30
            reasoning.append("Below action threshold. No intervention recommended.")

        # Low CSAT boosts urgency note
        if csat < 2.5:
            reasoning.append(
                f"⚠ CSAT {csat:.1f} is critically low — include service recovery messaging."
            )

        return AgentOutput(
            agent_name="CustomerAgent",
            domain=Domain.CUSTOMER,
            decision_type=DecisionType.RETAIN_CUSTOMER,
            entity_id=context.entity_id,
            recommended_action=action,
            quantity=None,
            urgency_hours=24.0 if tier.startswith("P1") else 72.0,
            confidence=round(min(confidence, 1.0), 4),
            reasoning_steps=reasoning,
            evidence={
                "churn_probability":   churn_prob,
                "risk_tier":           preds["risk_tier"],
                "total_spend_gbp":     total_spend,
                "is_high_value":       is_high_val,
                "tenure_days":         tenure_days,
                "avg_csat_score":      csat,
                "retention_tier":      tier,
                "channel":             channel,
            },
            source_models=["churn_xgboost_scale_pos_weight"],
            run_id=context.run_id,
        )
