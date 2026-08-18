"""
data_science/agents/operations_agent.py
=========================================
Stage 10 — OperationsAgent

Consumes machine health predictions (analytics.fact_predictions_machine_health)
to produce SCHEDULE_MAINTENANCE decisions.

Urgency tiers:
  IMMEDIATE  (≤ 4h)  — failure_prob_24h ≥ 0.80 OR health_status = Critical
  PREVENTIVE (≤ 24h) — failure_prob_24h ≥ 0.50 OR is_anomaly_flag = 1
  MONITOR            — all other anomalous machines (below thresholds)
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

# Urgency thresholds
IMMEDIATE_PROB  = 0.80
PREVENTIVE_PROB = 0.50


class OperationsAgent(BaseAgent):
    """
    Analyses machine telemetry health predictions to recommend
    maintenance scheduling actions.

    Reads the latest per-machine prediction from
    analytics.fact_predictions_machine_health and groups by machine_id,
    taking the maximum failure probability and anomaly score per machine.
    """

    agent_name = "OperationsAgent"
    domain     = "operations"
    version    = "1.0.0"

    def __init__(self, db_engine=None):
        super().__init__()
        self.engine = db_engine or get_engine()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_contexts(self) -> List[AgentContext]:
        """
        Load latest machine health predictions, aggregate per machine,
        and return AgentContext for machines requiring attention.
        """
        query = text("""
            WITH agg_per_machine AS (
                SELECT
                    machine_id,
                    MAX(anomaly_score)         AS anomaly_score,
                    MAX(is_anomaly_flag)        AS is_anomaly_flag,
                    MAX(failure_prob_24h)       AS failure_prob_24h,
                    MAX(failure_alert_flag_24h) AS failure_alert_flag_24h,
                    -- health_status: Critical > Warning > Normal (use worst)
                    CASE
                        WHEN MAX(CASE health_status WHEN 'Critical' THEN 2
                                                    WHEN 'Warning'  THEN 1
                                                    ELSE 0 END) = 2 THEN 'Critical'
                        WHEN MAX(CASE health_status WHEN 'Critical' THEN 2
                                                    WHEN 'Warning'  THEN 1
                                                    ELSE 0 END) = 1 THEN 'Warning'
                        ELSE 'Normal'
                    END                        AS health_status,
                    MAX(model_version)          AS model_version,
                    MAX(minute_timestamp)       AS minute_timestamp
                FROM analytics.fact_predictions_machine_health
                GROUP BY machine_id
            )
            SELECT *
            FROM agg_per_machine
            WHERE is_anomaly_flag = 1
               OR failure_prob_24h >= :min_prob
               OR health_status IN ('Warning', 'Critical')
            ORDER BY failure_prob_24h DESC, anomaly_score DESC
        """)

        try:
            df = pd.read_sql(
                query, self.engine,
                params={"min_prob": PREVENTIVE_PROB}
            )
        except Exception as exc:
            logger.warning("OperationsAgent: DB query failed (%s). Returning empty.", exc)
            return []

        if df.empty:
            logger.info("OperationsAgent: No machines requiring attention.")
            return []

        run_id = uuid.uuid4()
        contexts = []
        for _, row in df.iterrows():
            ctx = AgentContext(
                domain=Domain.OPERATIONS,
                entity_id=str(row["machine_id"]),
                predictions={
                    "anomaly_score":         float(row["anomaly_score"]),
                    "is_anomaly_flag":       int(row["is_anomaly_flag"]),
                    "failure_prob_24h":      float(row["failure_prob_24h"]),
                    "failure_alert_flag_24h":int(row["failure_alert_flag_24h"]),
                    "health_status":         str(row["health_status"]),
                    "model_version":         str(row["model_version"]),
                },
                business_ctx={
                    "last_reading_ts": str(row["minute_timestamp"]),
                },
                run_id=run_id,
            )
            contexts.append(ctx)

        logger.info("OperationsAgent: Loaded %d machine contexts requiring action.", len(contexts))
        return contexts

    # ------------------------------------------------------------------
    # Core reasoning
    # ------------------------------------------------------------------

    def analyze(self, context: AgentContext) -> AgentOutput:
        """Assign maintenance urgency tier and produce SCHEDULE_MAINTENANCE recommendation."""
        preds  = context.predictions
        bctx   = context.business_ctx

        failure_prob  = preds["failure_prob_24h"]
        anomaly_score = preds["anomaly_score"]
        is_anomaly    = bool(preds["is_anomaly_flag"])
        health_status = preds["health_status"]
        last_ts       = bctx.get("last_reading_ts", "unknown")

        reasoning: List[str] = []
        reasoning.append(
            f"Machine {context.entity_id}: health_status={health_status}, "
            f"failure_prob_24h={failure_prob:.1%}, anomaly_score={anomaly_score:.4f}"
        )
        reasoning.append(f"Last telemetry reading: {last_ts}")

        # Tier assignment
        # Primary signal: failure_prob_24h (Random Forest, calibrated)
        # Secondary signal: anomaly_score (IsolationForest, less specific)
        if failure_prob >= IMMEDIATE_PROB:
            tier          = "IMMEDIATE"
            urgency_hours = 4.0
            action = (
                f"IMMEDIATE maintenance required for {context.entity_id} within 4 hours. "
                f"24h failure probability: {failure_prob:.1%}. "
                f"Dispatch maintenance team now."
            )
            confidence = failure_prob * 0.95
            reasoning.append(
                f"IMMEDIATE trigger: failure_prob_24h {failure_prob:.1%} >= {IMMEDIATE_PROB:.0%}. "
                f"4-hour maintenance window."
            )

        elif failure_prob >= PREVENTIVE_PROB or (is_anomaly and failure_prob > 0):
            tier          = "PREVENTIVE"
            urgency_hours = 24.0
            action = (
                f"PREVENTIVE maintenance recommended for {context.entity_id} within 24 hours. "
                f"24h failure probability: {failure_prob:.1%}. "
                f"Anomaly detected: {is_anomaly}. Schedule diagnostic inspection."
            )
            confidence = max(failure_prob, anomaly_score * 0.5) * 0.90
            reasoning.append(
                f"PREVENTIVE trigger: failure_prob_24h {failure_prob:.1%} >= {PREVENTIVE_PROB:.0%} "
                f"OR (is_anomaly={is_anomaly} AND failure_prob > 0). 24-hour window."
            )

        elif is_anomaly:
            tier          = "MONITOR"
            urgency_hours = 72.0
            action = (
                f"MONITOR {context.entity_id}: anomaly detected but failure risk is low "
                f"(failure_prob_24h={failure_prob:.1%}). Increase telemetry check frequency."
            )
            confidence = anomaly_score * 0.6
            reasoning.append(
                "MONITOR: anomaly present but no failure probability signal. "
                "Continue monitoring with increased frequency."
            )

        else:
            tier          = "MONITOR"
            urgency_hours = 72.0
            action = (
                f"MONITOR {context.entity_id}: low-risk anomaly pattern "
                f"(failure_prob_24h={failure_prob:.1%}). Standard monitoring interval."
            )
            confidence = 0.40
            reasoning.append(
                "MONITOR: below all urgency thresholds. Standard monitoring."
            )

        # Anomaly score context
        if anomaly_score > 0.5:
            reasoning.append(
                f"Elevated anomaly score ({anomaly_score:.4f} > 0.5) — "
                "likely deviation from normal operating envelope."
            )

        return AgentOutput(
            agent_name="OperationsAgent",
            domain=Domain.OPERATIONS,
            decision_type=DecisionType.SCHEDULE_MAINTENANCE,
            entity_id=context.entity_id,
            recommended_action=action,
            quantity=None,
            urgency_hours=urgency_hours,
            confidence=round(min(confidence, 1.0), 4),
            reasoning_steps=reasoning,
            evidence={
                "failure_prob_24h":  failure_prob,
                "anomaly_score":     anomaly_score,
                "is_anomaly_flag":   is_anomaly,
                "health_status":     health_status,
                "urgency_tier":      tier,
                "urgency_hours":     urgency_hours,
            },
            source_models=["machine_isolation_forest", "machine_failure_random_forest"],
            run_id=context.run_id,
        )
