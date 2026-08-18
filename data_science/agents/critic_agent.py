"""
data_science/agents/critic_agent.py
=====================================
Stage 10 — CriticAgent

Receives all 4 domain agent outputs and challenges recommendations
that are quantitatively inconsistent with the underlying evidence.

The CriticAgent does NOT approve or reject — it produces a CriticChallenge
for each AgentOutput, which may include a revised quantity or revised action.
The final verdict is determined downstream by the DecisionManager.

Challenge rules applied:
  1. Inventory: reorder_qty > 2 × demand_7d → challenge and revise downward
  2. Customer:  churn_prob < 0.60 but P1 intervention recommended → flag as over-intervention
  3. Operations: is_anomaly=True but failure_prob < 0.30 → downgrade IMMEDIATE to PREVENTIVE
  4. Demand:    INCREASE_STOCK_ORDER recommended while stockout risk is CRITICAL → conflict flag
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from data_science.agents.schemas import (
    AgentOutput,
    CriticChallenge,
    Domain,
    RiskLevel,
)

logger = logging.getLogger(__name__)

# Challenge thresholds
INVENTORY_EXCESS_MULTIPLIER     = 2.0    # reorder > 2× demand_7d triggers challenge
CHURN_MIN_CONFIDENCE_P1         = 0.60   # below this, P1 is over-intervention
OPS_ANOMALY_LOW_FAILURE_THRESH  = 0.30   # anomaly present but failure below this → downgrade
SAFETY_BUFFER_FRACTION          = 0.90   # revised reorder = demand_7d × this


class CriticAgent:
    """
    Adversarial governance agent that challenges domain agent recommendations
    using quantitative rules derived from the prediction evidence.

    Does not inherit BaseAgent — operates at the orchestration layer,
    receiving a batch of AgentOutput objects rather than raw prediction contexts.
    """

    agent_name = "CriticAgent"
    version    = "1.0.0"

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def challenge_all(
        self,
        outputs: List[AgentOutput],
        # Optional: pass cross-domain context for cross-agent challenges
        stockout_alerts: Optional[Dict[str, float]] = None,
    ) -> Dict[str, CriticChallenge]:
        """
        Challenge all domain agent outputs.

        Args:
            outputs: List of AgentOutput from all domain agents
            stockout_alerts: Optional dict of entity_id → stockout_prob for
                             cross-domain inventory/demand conflict detection

        Returns:
            Dict mapping entity_id → CriticChallenge
            (no_challenge entries have challenge_raised=False)
        """
        stockout_alerts = stockout_alerts or {}
        challenges: Dict[str, CriticChallenge] = {}

        for output in outputs:
            try:
                challenge = self._challenge_single(output, stockout_alerts)
                # Key by entity_id + domain to handle same entity across domains
                key = f"{output.domain.value}::{output.entity_id}"
                challenges[key] = challenge
            except Exception as exc:
                self.logger.error(
                    "CriticAgent failed on %s::%s — %s",
                    output.domain.value, output.entity_id, exc, exc_info=True
                )
                # Emit no-challenge on error so we don't block decisions
                key = f"{output.domain.value}::{output.entity_id}"
                challenges[key] = CriticChallenge(
                    domain=output.domain,
                    entity_id=output.entity_id,
                    challenge_raised=False,
                )

        challenged = sum(1 for c in challenges.values() if c.challenge_raised)
        self.logger.info(
            "CriticAgent: reviewed %d recommendations, raised %d challenges.",
            len(outputs), challenged
        )
        return challenges

    # ------------------------------------------------------------------
    # Internal routing
    # ------------------------------------------------------------------

    def _challenge_single(
        self,
        output: AgentOutput,
        stockout_alerts: Dict[str, float],
    ) -> CriticChallenge:
        if output.domain == Domain.INVENTORY:
            return self._challenge_inventory(output)
        elif output.domain == Domain.CUSTOMER:
            return self._challenge_customer(output)
        elif output.domain == Domain.OPERATIONS:
            return self._challenge_operations(output)
        elif output.domain == Domain.DEMAND:
            return self._challenge_demand(output, stockout_alerts)
        else:
            return CriticChallenge(
                domain=output.domain,
                entity_id=output.entity_id,
                challenge_raised=False,
            )

    # ------------------------------------------------------------------
    # Rule 1: Inventory — excess reorder quantity
    # ------------------------------------------------------------------

    def _challenge_inventory(self, output: AgentOutput) -> CriticChallenge:
        evidence    = output.evidence
        demand_7d   = evidence.get("demand_7d", 0.0)
        reorder_qty = output.quantity or 0.0

        if demand_7d <= 0:
            return CriticChallenge(domain=output.domain, entity_id=output.entity_id)

        excess_threshold = demand_7d * INVENTORY_EXCESS_MULTIPLIER

        if reorder_qty > excess_threshold:
            revised = round(demand_7d * SAFETY_BUFFER_FRACTION)
            excess  = reorder_qty - demand_7d
            text = (
                f"Proposed reorder of {reorder_qty:.0f} units exceeds 2× the 7-day demand "
                f"forecast ({demand_7d:.1f} units). Current inventory covers "
                f"{evidence.get('quantity_available', 0):.0f} units. "
                f"Ordering {reorder_qty:.0f} creates {excess:.0f} units excess exposure. "
                f"Recommend revising to {revised} units "
                f"(= demand_7d × {SAFETY_BUFFER_FRACTION})."
            )
            self.logger.info(
                "CriticAgent [INVENTORY] challenged %s: reorder %s→%s (demand_7d=%.1f)",
                output.entity_id, reorder_qty, revised, demand_7d
            )
            return CriticChallenge(
                domain=output.domain,
                entity_id=output.entity_id,
                challenge_raised=True,
                challenge_text=text,
                revised_quantity=float(revised),
                revised_action=(
                    f"REORDER {revised} units of {output.entity_id} "
                    f"from {evidence.get('supplier', 'supplier')} "
                    f"[CRITIC REVISED from {reorder_qty:.0f}]."
                ),
                severity=RiskLevel.MEDIUM,
            )

        return CriticChallenge(domain=output.domain, entity_id=output.entity_id)

    # ------------------------------------------------------------------
    # Rule 2: Customer — low-confidence P1 intervention
    # ------------------------------------------------------------------

    def _challenge_customer(self, output: AgentOutput) -> CriticChallenge:
        evidence     = output.evidence
        churn_prob   = evidence.get("churn_probability", 0.0)
        tier         = evidence.get("retention_tier", "")

        if tier.startswith("P1") and churn_prob < CHURN_MIN_CONFIDENCE_P1:
            text = (
                f"Churn probability {churn_prob:.1%} is below the high-confidence threshold "
                f"({CHURN_MIN_CONFIDENCE_P1:.0%}) for P1 intervention. "
                f"ROI on phone + discount at this confidence level is uncertain. "
                f"Recommend downgrading to P2 (email-only) intervention."
            )
            self.logger.info(
                "CriticAgent [CUSTOMER] challenged %s: P1 downgrade (prob=%.2f)",
                output.entity_id, churn_prob
            )
            return CriticChallenge(
                domain=output.domain,
                entity_id=output.entity_id,
                challenge_raised=True,
                challenge_text=text,
                revised_action=(
                    f"STANDARD retention: send re-engagement email to {output.entity_id}. "
                    "[CRITIC REVISED: P1→P2 due to sub-threshold churn probability]"
                ),
                severity=RiskLevel.LOW,
            )

        return CriticChallenge(domain=output.domain, entity_id=output.entity_id)

    # ------------------------------------------------------------------
    # Rule 3: Operations — anomaly flag but low failure probability
    # ------------------------------------------------------------------

    def _challenge_operations(self, output: AgentOutput) -> CriticChallenge:
        evidence     = output.evidence
        failure_prob = evidence.get("failure_prob_24h", 0.0)
        is_anomaly   = evidence.get("is_anomaly_flag", False)
        tier         = evidence.get("urgency_tier", "")

        if is_anomaly and failure_prob < OPS_ANOMALY_LOW_FAILURE_THRESH and tier == "IMMEDIATE":
            text = (
                f"Anomaly flag is set but 24h failure probability is only {failure_prob:.1%} "
                f"(below {OPS_ANOMALY_LOW_FAILURE_THRESH:.0%}). "
                f"IMMEDIATE dispatch is disproportionate. "
                f"Recommend downgrading to PREVENTIVE maintenance (24-hour window) "
                f"with enhanced monitoring."
            )
            self.logger.info(
                "CriticAgent [OPERATIONS] challenged %s: IMMEDIATE→PREVENTIVE (prob=%.2f)",
                output.entity_id, failure_prob
            )
            return CriticChallenge(
                domain=output.domain,
                entity_id=output.entity_id,
                challenge_raised=True,
                challenge_text=text,
                revised_action=(
                    f"PREVENTIVE maintenance for {output.entity_id} within 24 hours "
                    f"[CRITIC REVISED: IMMEDIATE→PREVENTIVE, failure_prob={failure_prob:.1%}]."
                ),
                severity=RiskLevel.LOW,
            )

        return CriticChallenge(domain=output.domain, entity_id=output.entity_id)

    # ------------------------------------------------------------------
    # Rule 4: Demand — increase order while stockout risk is CRITICAL
    # ------------------------------------------------------------------

    def _challenge_demand(
        self,
        output: AgentOutput,
        stockout_alerts: Dict[str, float],
    ) -> CriticChallenge:
        evidence    = output.evidence
        direction   = evidence.get("direction", "")
        stockout_p  = stockout_alerts.get(output.entity_id, 0.0)

        # Conflict: DemandAgent says increase order, but stockout agent
        # already flagged this SKU as critical — they may be independent
        # channels to the same problem; the critic notes the conflict.
        if direction == "INCREASE_STOCK_ORDER" and stockout_p >= 0.80:
            text = (
                f"DemandAgent recommends INCREASE_STOCK_ORDER for {output.entity_id}, "
                f"but Inventory stockout risk is already CRITICAL ({stockout_p:.1%}). "
                f"Confirm the InventoryAgent has already generated a reorder recommendation "
                f"for this SKU to avoid duplicate orders."
            )
            self.logger.info(
                "CriticAgent [DEMAND] flagged %s: duplicate order risk (stockout=%.2f)",
                output.entity_id, stockout_p
            )
            return CriticChallenge(
                domain=output.domain,
                entity_id=output.entity_id,
                challenge_raised=True,
                challenge_text=text,
                revised_action=None,   # not revising action, just flagging
                severity=RiskLevel.MEDIUM,
            )

        return CriticChallenge(domain=output.domain, entity_id=output.entity_id)
