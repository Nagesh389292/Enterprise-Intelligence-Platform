"""
data_science/agents/decision_manager.py
=========================================
Stage 10 — DecisionManager

Receives (AgentOutput, CriticChallenge, RiskAssessment) triplets
from the AgentBus and:
  1. Applies final verdict logic
  2. Assembles canonical Decision objects
  3. Persists batch to analytics.agent_decisions (PostgreSQL)
  4. Exports JSON audit log to docs/agents/decision_audit_{YYYYMMDD}.json

Verdict rules:
  ESCALATED                — risk_level=CRITICAL AND adjusted_confidence < 0.50
  REJECTED                 — critic fully rejected action (challenge_raised + no revised_action + HIGH+ severity)
  APPROVED_WITH_CONDITIONS — requires_human_approval=True OR critic revised quantity
  APPROVED                 — all other passing cases
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import text

from data_science.db import get_engine
from data_science.agents.schemas import (
    AgentOutput,
    CriticChallenge,
    RiskAssessment,
    Decision,
    DecisionType,
    Domain,
    RiskLevel,
    Verdict,
)

logger = logging.getLogger(__name__)

# Human approval confidence threshold (must match RiskAgent)
CONFIDENCE_APPROVAL_GATE = 0.65
ESCALATE_CONFIDENCE_GATE = 0.50

# Output paths
AUDIT_LOG_DIR = Path("docs/agents")


class DecisionManager:
    """
    Assembles final Decision objects, applies verdict logic,
    persists to PostgreSQL, and exports JSON audit log.
    """

    def __init__(self, db_engine=None):
        self.engine = db_engine or get_engine()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def produce_decisions(
        self,
        outputs: List[AgentOutput],
        challenges: Dict[str, CriticChallenge],
        assessments: Dict[str, RiskAssessment],
        run_id: uuid.UUID,
    ) -> List[Decision]:
        """
        Assemble Decision objects from domain agent outputs,
        critic challenges, and risk assessments.

        Persists the batch to DB and writes the JSON audit log.
        Returns the list of Decision objects.
        """
        decisions: List[Decision] = []

        for output in outputs:
            key        = f"{output.domain.value}::{output.entity_id}"
            challenge  = challenges.get(key)
            assessment = assessments.get(key)

            if assessment is None:
                logger.warning("No RiskAssessment for %s — skipping.", key)
                continue

            decision = self._assemble_decision(output, challenge, assessment, run_id)
            decisions.append(decision)

        # Persist to PostgreSQL
        if decisions:
            self._persist_to_db(decisions)
            self._export_json_audit(decisions, run_id)

        return decisions

    # ------------------------------------------------------------------
    # Decision assembly
    # ------------------------------------------------------------------

    def _assemble_decision(
        self,
        output: AgentOutput,
        challenge: Optional[CriticChallenge],
        assessment: RiskAssessment,
        run_id: uuid.UUID,
    ) -> Decision:
        """Apply verdict logic and build the canonical Decision object."""

        # Apply critic revisions to action/quantity
        recommended_action = output.recommended_action
        quantity           = output.quantity
        urgency_hours      = output.urgency_hours
        critic_text        = None

        if challenge and challenge.challenge_raised:
            critic_text = challenge.challenge_text
            if challenge.revised_action:
                recommended_action = challenge.revised_action
            if challenge.revised_quantity is not None:
                quantity = challenge.revised_quantity

        # Build full reasoning chain
        reasoning_chain = list(output.reasoning_steps)
        if critic_text:
            reasoning_chain.append(f"[CriticAgent] {critic_text}")
        for factor in assessment.risk_factors:
            reasoning_chain.append(f"[RiskAgent] {factor}")

        # Final verdict
        verdict = self._determine_verdict(output, challenge, assessment)

        # Confidence score = risk-adjusted confidence from RiskAgent
        confidence_score = assessment.adjusted_confidence

        return Decision(
            decision_id=uuid.uuid4(),
            run_id=run_id,
            domain=output.domain,
            decision_type=output.decision_type,
            entity_id=output.entity_id,
            recommended_action=recommended_action,
            quantity=quantity,
            urgency_hours=urgency_hours,
            confidence_score=confidence_score,
            risk_level=assessment.overall_risk_level,
            requires_human_approval=assessment.requires_human_approval,
            reasoning_chain=reasoning_chain,
            critic_challenge=critic_text,
            risk_assessment={
                "financial_exposure_usd":    assessment.financial_exposure_usd,
                "model_confidence":          assessment.model_confidence,
                "model_uncertainty_penalty": assessment.model_uncertainty_penalty,
                "adjusted_confidence":       assessment.adjusted_confidence,
                "requires_human_approval":   assessment.requires_human_approval,
                "risk_factors":              assessment.risk_factors,
            },
            source_models=output.source_models,
            final_verdict=verdict,
            created_at=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------
    # Verdict logic
    # ------------------------------------------------------------------

    def _determine_verdict(
        self,
        output: AgentOutput,
        challenge: Optional[CriticChallenge],
        assessment: RiskAssessment,
    ) -> Verdict:
        """Apply the four-tier verdict logic."""

        adj_conf   = assessment.adjusted_confidence
        risk_level = assessment.overall_risk_level

        # ESCALATED: critical risk + very low confidence
        if risk_level == RiskLevel.CRITICAL and adj_conf < ESCALATE_CONFIDENCE_GATE:
            return Verdict.ESCALATED

        # REJECTED: critic raised challenge AND no revised action AND HIGH+ severity
        if (
            challenge
            and challenge.challenge_raised
            and challenge.revised_action is None
            and challenge.severity in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        ):
            return Verdict.REJECTED

        # APPROVED_WITH_CONDITIONS: human approval required OR critic revised quantity
        if (
            assessment.requires_human_approval
            or (challenge and challenge.challenge_raised and challenge.revised_quantity is not None)
        ):
            return Verdict.APPROVED_WITH_CONDITIONS

        # Default: APPROVED
        return Verdict.APPROVED

    # ------------------------------------------------------------------
    # DB persistence
    # ------------------------------------------------------------------

    def _persist_to_db(self, decisions: List[Decision]) -> None:
        """Batch-insert Decision objects into analytics.agent_decisions."""
        rows = [d.to_db_row() for d in decisions]

        insert_sql = text("""
            INSERT INTO analytics.agent_decisions (
                decision_id, run_id, domain, decision_type, entity_id,
                recommended_action, quantity, urgency_hours,
                confidence_score, risk_level, requires_human_approval,
                reasoning_chain, critic_challenge, risk_assessment,
                source_models, final_verdict, created_at
            ) VALUES (
                :decision_id, :run_id, :domain, :decision_type, :entity_id,
                :recommended_action, :quantity, :urgency_hours,
                :confidence_score, :risk_level, :requires_human_approval,
                CAST(:reasoning_chain AS jsonb), :critic_challenge, CAST(:risk_assessment AS jsonb),
                :source_models, :final_verdict, :created_at
            )
            ON CONFLICT (decision_id) DO NOTHING
        """)

        try:
            with self.engine.begin() as conn:
                for row in rows:
                    conn.execute(insert_sql, row)
            logger.info(
                "DecisionManager: persisted %d decisions to analytics.agent_decisions.",
                len(rows)
            )
        except Exception as exc:
            logger.error("DecisionManager: DB persist failed — %s", exc, exc_info=True)

    # ------------------------------------------------------------------
    # JSON audit log
    # ------------------------------------------------------------------

    def _export_json_audit(self, decisions: List[Decision], run_id: uuid.UUID) -> None:
        """Serialize all decisions to a dated JSON audit log."""
        AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        date_str  = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        file_path = AUDIT_LOG_DIR / f"decision_audit_{date_str}.json"

        audit = {
            "run_id":        str(run_id),
            "generated_at":  datetime.now(timezone.utc).isoformat(),
            "total_decisions": len(decisions),
            "summary": {
                "by_domain":  self._count_by(decisions, "domain"),
                "by_verdict": self._count_by(decisions, "final_verdict"),
                "by_risk":    self._count_by(decisions, "risk_level"),
                "requiring_human_approval": sum(
                    1 for d in decisions if d.requires_human_approval
                ),
            },
            "decisions": [
                {
                    "decision_id":             str(d.decision_id),
                    "domain":                  d.domain.value,
                    "decision_type":           d.decision_type.value,
                    "entity_id":               d.entity_id,
                    "recommended_action":      d.recommended_action,
                    "quantity":                d.quantity,
                    "urgency_hours":           d.urgency_hours,
                    "confidence_score":        d.confidence_score,
                    "risk_level":              d.risk_level.value,
                    "requires_human_approval": d.requires_human_approval,
                    "final_verdict":           d.final_verdict.value,
                    "source_models":           d.source_models,
                    "critic_challenge":        d.critic_challenge,
                    "reasoning_chain":         d.reasoning_chain,
                    "risk_assessment":         d.risk_assessment,
                    "created_at":              d.created_at.isoformat(),
                }
                for d in decisions
            ],
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(audit, f, indent=2, default=str)
            logger.info("DecisionManager: audit log written to %s", file_path)
        except Exception as exc:
            logger.error("DecisionManager: JSON audit export failed — %s", exc)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _count_by(self, decisions: List[Decision], attr: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for d in decisions:
            val = getattr(d, attr)
            key = val.value if hasattr(val, "value") else str(val)
            counts[key] = counts.get(key, 0) + 1
        return counts
