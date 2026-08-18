"""
data_science/agents/schemas.py
================================
Stage 10 — All Pydantic v2 schemas for the multi-agent decision system.

Provides:
  - Enums: Domain, DecisionType, RiskLevel, Verdict
  - AgentContext  — structured input to any domain agent
  - AgentOutput   — recommendation from a domain agent
  - CriticChallenge — CriticAgent's structured challenge to a recommendation
  - RiskAssessment  — RiskAgent's financial/operational scoring output
  - Decision        — canonical final decision object (persisted to DB + JSON log)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Domain(str, Enum):
    CUSTOMER   = "customer"
    INVENTORY  = "inventory"
    OPERATIONS = "operations"
    DEMAND     = "demand"


class DecisionType(str, Enum):
    RETAIN_CUSTOMER      = "RETAIN_CUSTOMER"
    REORDER_INVENTORY    = "REORDER_INVENTORY"
    SCHEDULE_MAINTENANCE = "SCHEDULE_MAINTENANCE"
    ADJUST_DEMAND_PLAN   = "ADJUST_DEMAND_PLAN"


class RiskLevel(str, Enum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


class Verdict(str, Enum):
    APPROVED                 = "APPROVED"
    APPROVED_WITH_CONDITIONS = "APPROVED_WITH_CONDITIONS"
    REJECTED                 = "REJECTED"
    ESCALATED                = "ESCALATED"


class RetentionChannel(str, Enum):
    EMAIL    = "EMAIL"
    PHONE    = "PHONE"
    DISCOUNT = "DISCOUNT"
    MONITOR  = "MONITOR"


class MaintenanceUrgency(str, Enum):
    IMMEDIATE  = "IMMEDIATE"    # ≤ 4 hours
    PREVENTIVE = "PREVENTIVE"   # ≤ 24 hours
    MONITOR    = "MONITOR"      # watch, no action yet


class DemandDirection(str, Enum):
    INCREASE_STOCK_ORDER  = "INCREASE_STOCK_ORDER"
    REDUCE_PURCHASE_ORDER = "REDUCE_PURCHASE_ORDER"
    RUN_PROMOTION         = "RUN_PROMOTION"
    MAINTAIN              = "MAINTAIN"


# ---------------------------------------------------------------------------
# AgentContext — inputs delivered to every agent by the AgentBus
# ---------------------------------------------------------------------------

class AgentContext(BaseModel):
    """
    Structured input payload for a single domain agent invocation.
    Contains the raw prediction data and any joined business context
    needed by the agent to form its recommendation.
    """
    domain:      Domain
    entity_id:   str              = Field(..., description="Primary entity: customer_id, product_id, or machine_id")
    predictions: Dict[str, Any]   = Field(default_factory=dict, description="Raw prediction values from the prediction store")
    business_ctx: Dict[str, Any]  = Field(default_factory=dict, description="Joined business context: LTV, inventory levels, supplier info, etc.")
    run_id:       uuid.UUID       = Field(default_factory=uuid.uuid4)
    as_of:        datetime        = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# AgentOutput — recommendation produced by a domain agent
# ---------------------------------------------------------------------------

class AgentOutput(BaseModel):
    """
    The recommendation produced by a single domain agent.
    Contains the proposed action, supporting evidence, and
    an initial confidence score.
    """
    agent_name:           str
    domain:               Domain
    decision_type:        DecisionType
    entity_id:            str
    recommended_action:   str           = Field(..., description="Human-readable action string")
    quantity:             Optional[float] = None   # reorder quantity (inventory) or None
    urgency_hours:        Optional[float] = None   # maintenance urgency window (operations) or None
    confidence:           float          = Field(..., ge=0.0, le=1.0)
    reasoning_steps:      List[str]      = Field(default_factory=list, description="Ordered human-readable reasoning steps")
    evidence:             Dict[str, Any] = Field(default_factory=dict, description="Key numeric evidence driving the recommendation")
    source_models:        List[str]      = Field(default_factory=list)
    run_id:               uuid.UUID

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(v, 4)


# ---------------------------------------------------------------------------
# CriticChallenge — CriticAgent's structured challenge to a recommendation
# ---------------------------------------------------------------------------

class CriticChallenge(BaseModel):
    """
    Structured challenge produced by the CriticAgent for one AgentOutput.
    If no challenge is warranted, `challenge_raised` is False and
    all other fields are None.
    """
    domain:            Domain
    entity_id:         str
    challenge_raised:  bool  = False
    challenge_text:    Optional[str]   = None    # human-readable challenge description
    revised_quantity:  Optional[float] = None    # critic-revised reorder quantity (inventory only)
    revised_action:    Optional[str]   = None    # critic-revised action string (if changed)
    severity:          Optional[RiskLevel] = None  # how seriously the critic views the issue


# ---------------------------------------------------------------------------
# RiskAssessment — RiskAgent's financial/operational scoring output
# ---------------------------------------------------------------------------

class RiskAssessment(BaseModel):
    """
    Financial exposure and operational risk scoring produced by the RiskAgent.
    Aggregates model confidence, financial exposure, and uncertainty penalties
    into a unified risk profile.
    """
    domain:                      Domain
    entity_id:                   str
    overall_risk_level:          RiskLevel
    financial_exposure_usd:      float   = Field(..., ge=0.0, description="Estimated dollar impact if decision is wrong")
    model_confidence:            float   = Field(..., ge=0.0, le=1.0, description="Raw model probability used as confidence proxy")
    model_uncertainty_penalty:   float   = Field(..., ge=0.0, le=1.0, description="Multiplier applied for known model weakness (e.g. low PR-AUC)")
    adjusted_confidence:         float   = Field(..., ge=0.0, le=1.0, description="model_confidence × (1 - model_uncertainty_penalty)")
    requires_human_approval:     bool
    risk_factors:                List[str] = Field(default_factory=list, description="Ordered list of specific risk factor descriptions")

    @field_validator("adjusted_confidence")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, round(v, 4)))


# ---------------------------------------------------------------------------
# Decision — canonical final decision object
# ---------------------------------------------------------------------------

class Decision(BaseModel):
    """
    The canonical, fully-auditable decision object produced by the DecisionManager.
    One Decision is persisted per entity per AgentBus run.
    Maps 1:1 to analytics.agent_decisions rows.
    """
    decision_id:             uuid.UUID      = Field(default_factory=uuid.uuid4)
    run_id:                  uuid.UUID

    # Domain & Entity
    domain:                  Domain
    decision_type:           DecisionType
    entity_id:               str

    # Final recommendation (post-critic revision)
    recommended_action:      str
    quantity:                Optional[float] = None
    urgency_hours:           Optional[float] = None

    # Risk & Confidence
    confidence_score:        float           = Field(..., ge=0.0, le=1.0)
    risk_level:              RiskLevel
    requires_human_approval: bool

    # Full audit trail
    reasoning_chain:         List[str]       = Field(default_factory=list)
    critic_challenge:        Optional[str]   = None
    risk_assessment:         Dict[str, Any]  = Field(default_factory=dict)
    source_models:           List[str]       = Field(default_factory=list)

    # Final verdict
    final_verdict:           Verdict

    # Timestamp
    created_at:              datetime        = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_db_row(self) -> Dict[str, Any]:
        """Serialize to a flat dict suitable for SQLAlchemy INSERT."""
        import json
        return {
            "decision_id":             str(self.decision_id),
            "run_id":                  str(self.run_id),
            "domain":                  self.domain.value,
            "decision_type":           self.decision_type.value,
            "entity_id":               self.entity_id,
            "recommended_action":      self.recommended_action,
            "quantity":                self.quantity,
            "urgency_hours":           self.urgency_hours,
            "confidence_score":        self.confidence_score,
            "risk_level":              self.risk_level.value,
            "requires_human_approval": self.requires_human_approval,
            "reasoning_chain":         json.dumps(self.reasoning_chain),
            "critic_challenge":        self.critic_challenge,
            "risk_assessment":         json.dumps(self.risk_assessment),
            "source_models":           self.source_models,
            "final_verdict":           self.final_verdict.value,
            "created_at":              self.created_at,
        }
