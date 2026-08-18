"""
data_science/agents/risk_agent.py
===================================
Stage 10 — RiskAgent

Receives domain agent outputs and their CriticChallenge objects.
Scores each recommendation on:
  - Financial exposure (revenue at risk, inventory cost, downtime cost)
  - Model confidence (raw probability from prediction store)
  - Model uncertainty penalty (applied for known model weaknesses)
  - Operational urgency
  - Human approval gate (confidence < 0.65 OR financial_exposure > threshold)

Known model uncertainty penalties applied (from Stage 8 audits):
  - Customer churn: PR-AUC = 0.0570 → weak signal → uncertainty_penalty = 0.30
  - SKU demand: WAPE = 61% → moderate uncertainty → uncertainty_penalty = 0.15
  - Inventory stockout: PR-AUC = 0.9425 → strong → uncertainty_penalty = 0.05
  - Machine failure: 100% event recall → strong → uncertainty_penalty = 0.05
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from data_science.agents.schemas import (
    AgentOutput,
    CriticChallenge,
    RiskAssessment,
    Domain,
    RiskLevel,
)

logger = logging.getLogger(__name__)

# Human approval thresholds
CONFIDENCE_APPROVAL_GATE   = 0.65      # below this → requires_human_approval = True
FINANCIAL_APPROVAL_GATE    = 50_000.0  # £50k+ financial exposure → requires approval

# Model uncertainty penalties (derived from Stage 8 audit results)
UNCERTAINTY_PENALTIES: Dict[str, float] = {
    "churn_xgboost_scale_pos_weight":            0.30,   # Stage 8A: PR-AUC 0.057
    "stockout_xgboost":                          0.05,   # Stage 8C: PR-AUC 0.9425
    "demand_ridge":                              0.15,   # Stage 8B: WAPE 61%
    "machine_isolation_forest":                  0.10,   # Stage 8D: unsupervised
    "machine_failure_random_forest":             0.05,   # Stage 8D: 100% event recall
}

# Estimated financial exposures by domain (per entity, per event)
# These are business assumptions — defensible in an interview
DOWNTIME_COST_PER_HOUR       = 2_000.0    # £/hour machine downtime
CHURN_REVENUE_MULTIPLIER     = 1.0        # use actual total_spend as exposure
EXCESS_INVENTORY_COST_RATE   = 0.20       # 20% of inventory value = holding cost
STOCKOUT_REVENUE_LOSS_FACTOR = 1.5        # lost sales = 1.5× unit cost × demand


class RiskAgent:
    """
    Financial and operational risk scorer for multi-agent decisions.

    Does not inherit BaseAgent — operates at the orchestration layer,
    receiving (AgentOutput, CriticChallenge) pairs rather than raw contexts.
    """

    agent_name = "RiskAgent"
    version    = "1.0.0"

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def assess_all(
        self,
        outputs: List[AgentOutput],
        challenges: Dict[str, "CriticChallenge"],
    ) -> Dict[str, RiskAssessment]:
        """
        Score all domain agent outputs.

        Args:
            outputs:    All domain AgentOutput objects
            challenges: Dict keyed by "domain::entity_id" from CriticAgent

        Returns:
            Dict mapping "domain::entity_id" → RiskAssessment
        """
        assessments: Dict[str, RiskAssessment] = {}

        for output in outputs:
            key = f"{output.domain.value}::{output.entity_id}"
            challenge = challenges.get(key)
            try:
                assessment = self._assess_single(output, challenge)
                assessments[key] = assessment
            except Exception as exc:
                self.logger.error(
                    "RiskAgent failed on %s — %s", key, exc, exc_info=True
                )
                # Emit a safe default (HIGH risk, requires approval) on error
                assessments[key] = RiskAssessment(
                    domain=output.domain,
                    entity_id=output.entity_id,
                    overall_risk_level=RiskLevel.HIGH,
                    financial_exposure_usd=0.0,
                    model_confidence=0.5,
                    model_uncertainty_penalty=0.20,
                    adjusted_confidence=0.40,
                    requires_human_approval=True,
                    risk_factors=["RiskAgent assessment failed — defaulting to HIGH risk."],
                )

        self.logger.info("RiskAgent: completed %d risk assessments.", len(assessments))
        return assessments

    # ------------------------------------------------------------------
    # Internal assessment
    # ------------------------------------------------------------------

    def _assess_single(
        self,
        output: AgentOutput,
        challenge: Optional["CriticChallenge"],
    ) -> RiskAssessment:
        domain   = output.domain
        evidence = output.evidence

        # 1. Model confidence = primary prediction probability
        model_confidence = self._extract_confidence(output, evidence)

        # 2. Uncertainty penalty = weighted average across source models
        uncertainty_penalty = self._compute_uncertainty_penalty(output.source_models)

        # 3. Adjusted confidence
        adjusted_confidence = model_confidence * (1.0 - uncertainty_penalty)

        # 4. Financial exposure
        financial_exposure = self._compute_financial_exposure(domain, evidence, output, challenge)

        # 5. Risk factors list
        risk_factors: List[str] = []

        if uncertainty_penalty >= 0.25:
            risk_factors.append(
                f"High model uncertainty penalty ({uncertainty_penalty:.0%}) — "
                f"source model(s) have known evaluation limitations."
            )
        if adjusted_confidence < CONFIDENCE_APPROVAL_GATE:
            risk_factors.append(
                f"Adjusted confidence {adjusted_confidence:.1%} is below approval gate "
                f"({CONFIDENCE_APPROVAL_GATE:.0%}). Human review recommended."
            )
        if financial_exposure >= FINANCIAL_APPROVAL_GATE:
            risk_factors.append(
                f"Financial exposure £{financial_exposure:,.0f} exceeds £{FINANCIAL_APPROVAL_GATE:,.0f} "
                f"approval gate."
            )
        if challenge and challenge.challenge_raised:
            risk_factors.append(
                f"CriticAgent raised a challenge: {challenge.severity.value if challenge.severity else 'MEDIUM'} severity."
            )

        # Domain-specific risk factors
        if domain == Domain.CUSTOMER:
            total_spend = evidence.get("total_spend_gbp", 0)
            if total_spend > 5_000:
                risk_factors.append(
                    f"High-value customer: £{total_spend:,.0f} lifetime spend at risk."
                )
        elif domain == Domain.OPERATIONS:
            urgency_hours = evidence.get("urgency_hours", 24.0)
            if urgency_hours <= 4:
                risk_factors.append(
                    "IMMEDIATE urgency: unplanned downtime within 4 hours possible."
                )
        elif domain == Domain.INVENTORY:
            stockout_prob = evidence.get("stockout_risk_prob_7d", 0.0)
            if stockout_prob >= 0.90:
                risk_factors.append(
                    f"Critical stockout risk ({stockout_prob:.0%}) — "
                    "revenue loss from out-of-stock imminent."
                )

        if not risk_factors:
            risk_factors.append("No significant risk factors identified.")

        # 6. Overall risk level
        overall_risk = self._compute_risk_level(
            adjusted_confidence, financial_exposure, domain, evidence, challenge
        )

        # 7. Human approval gate
        requires_approval = (
            adjusted_confidence < CONFIDENCE_APPROVAL_GATE
            or financial_exposure >= FINANCIAL_APPROVAL_GATE
            or overall_risk in (RiskLevel.CRITICAL,)
        )

        return RiskAssessment(
            domain=domain,
            entity_id=output.entity_id,
            overall_risk_level=overall_risk,
            financial_exposure_usd=round(financial_exposure, 2),
            model_confidence=round(model_confidence, 4),
            model_uncertainty_penalty=round(uncertainty_penalty, 4),
            adjusted_confidence=round(adjusted_confidence, 4),
            requires_human_approval=requires_approval,
            risk_factors=risk_factors,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_confidence(self, output: AgentOutput, evidence: dict) -> float:
        """Extract the most meaningful probability from evidence."""
        if output.domain == Domain.CUSTOMER:
            return evidence.get("churn_probability", output.confidence)
        elif output.domain == Domain.INVENTORY:
            return evidence.get("stockout_risk_prob_7d", output.confidence)
        elif output.domain == Domain.OPERATIONS:
            return evidence.get("failure_prob_24h", output.confidence)
        else:
            return output.confidence

    def _compute_uncertainty_penalty(self, source_models: List[str]) -> float:
        """Weighted average uncertainty penalty across source models."""
        if not source_models:
            return 0.20
        penalties = [
            UNCERTAINTY_PENALTIES.get(m, 0.10)
            for m in source_models
        ]
        return sum(penalties) / len(penalties)

    def _compute_financial_exposure(
        self,
        domain: Domain,
        evidence: dict,
        output: AgentOutput,
        challenge: Optional["CriticChallenge"],
    ) -> float:
        """Estimate financial exposure (£) for this recommendation."""
        if domain == Domain.CUSTOMER:
            # Revenue at risk = customer's total historical spend
            return float(evidence.get("total_spend_gbp", 0.0)) * CHURN_REVENUE_MULTIPLIER

        elif domain == Domain.INVENTORY:
            # Excess inventory cost if critic challenged the reorder quantity
            reorder_qty = (
                challenge.revised_quantity
                if (challenge and challenge.challenge_raised and challenge.revised_quantity)
                else (output.quantity or 0.0)
            )
            unit_cost   = evidence.get("unit_cost", 5.0) or 5.0
            return reorder_qty * unit_cost

        elif domain == Domain.OPERATIONS:
            # Downtime cost = urgency_hours × rate (if IMMEDIATE or PREVENTIVE)
            tier = evidence.get("urgency_tier", "MONITOR")
            urgency = evidence.get("urgency_hours", 72.0)
            if tier in ("IMMEDIATE", "PREVENTIVE") or urgency <= 24.0:
                return urgency * DOWNTIME_COST_PER_HOUR
            return 0.0

        elif domain == Domain.DEMAND:
            # Revenue impact = magnitude × unit_price
            magnitude  = evidence.get("magnitude", 0.0) or 0.0
            unit_price = evidence.get("unit_price", 0.0) or 0.0
            return magnitude * unit_price

        return 0.0

    def _compute_risk_level(
        self,
        adjusted_confidence: float,
        financial_exposure: float,
        domain: Domain,
        evidence: dict,
        challenge: Optional["CriticChallenge"],
    ) -> RiskLevel:
        """Derive overall risk level from confidence, exposure, and domain signals."""
        # CRITICAL: very low confidence + high exposure
        if adjusted_confidence < 0.40 and financial_exposure >= 10_000:
            return RiskLevel.CRITICAL

        # CRITICAL: operations IMMEDIATE urgency
        if domain == Domain.OPERATIONS and evidence.get("urgency_hours", 24) <= 4:
            return RiskLevel.CRITICAL

        # HIGH: low confidence OR high exposure OR critic challenge with MEDIUM+ severity
        if (
            adjusted_confidence < CONFIDENCE_APPROVAL_GATE
            or financial_exposure >= FINANCIAL_APPROVAL_GATE
            or (challenge and challenge.challenge_raised and
                challenge.severity in (RiskLevel.HIGH, RiskLevel.CRITICAL))
        ):
            return RiskLevel.HIGH

        # MEDIUM: moderate confidence or minor critic challenge
        if adjusted_confidence < 0.75 or (challenge and challenge.challenge_raised):
            return RiskLevel.MEDIUM

        return RiskLevel.LOW
