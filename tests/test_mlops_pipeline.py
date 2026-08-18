"""
tests/test_mlops_pipeline.py
=============================
Stage 11 — MLOps Retraining, Evaluation Gating & Pipeline Test Suite
"""

import os
import sys
import pytest
import joblib
import numpy as np
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from data_science.mlops.retrain import DomainRetrainer, VALID_DOMAINS
from data_science.mlops.evaluator import ModelEvaluator, EvaluationReport
from scripts.run_mlops_pipeline import run_pipeline


class DegradedDummyModel:
    """Dummy model that always predicts 0.0 probability to trigger gate failure."""
    def predict_proba(self, X):
        return np.zeros((len(X), 2))


class TestDomainRetrainer:
    """Verify targeted retraining engine for all 4 domains."""

    def test_valid_domains_list(self):
        assert set(VALID_DOMAINS) == {"churn", "demand", "stockout", "machine_health"}

    def test_invalid_domain_raises_error(self):
        retrainer = DomainRetrainer()
        with pytest.raises(ValueError, match="Invalid domain"):
            retrainer.retrain_domain("non_existent_domain")

    def test_retrain_demand_candidate(self, tmp_path):
        retrainer = DomainRetrainer(output_dir=str(tmp_path))
        res = retrainer.retrain_domain("demand")
        assert res["domain"] == "demand"
        assert os.path.exists(res["candidate_path"])

    def test_retrain_churn_candidate(self, tmp_path):
        retrainer = DomainRetrainer(output_dir=str(tmp_path))
        res = retrainer.retrain_domain("churn")
        assert res["domain"] == "churn"
        assert os.path.exists(res["candidate_path"])


class TestModelEvaluatorGating:
    """Verify champion vs challenger evaluation gates."""

    def test_missing_candidate_artifact_fails_gate(self):
        evaluator = ModelEvaluator()
        report = evaluator.evaluate_and_gate("demand", "non_existent_candidate.pkl")
        assert not report.passed_gate
        assert "missing" in report.rationale.lower()

    def test_demand_evaluator_gating(self, tmp_path):
        retrainer = DomainRetrainer(output_dir=str(tmp_path))
        ret_res = retrainer.retrain_domain("demand")
        candidate_path = ret_res["candidate_path"]

        evaluator = ModelEvaluator()
        report = evaluator.evaluate_and_gate("demand", candidate_path)

        assert isinstance(report, EvaluationReport)
        assert report.domain == "demand"
        assert "wape" in report.candidate_metrics
        assert "rmse" in report.candidate_metrics
        assert report.passed_gate is True

    def test_evaluator_rejects_degraded_model(self, tmp_path):
        dummy_path = tmp_path / "dummy_churn.pkl"
        joblib.dump({"model": DegradedDummyModel(), "optimal_threshold": 0.11}, dummy_path)

        evaluator = ModelEvaluator()
        report = evaluator.evaluate_and_gate("churn", str(dummy_path))

        assert report.passed_gate is False
        assert report.candidate_metrics.get("recall", 0.0) < 0.65
        assert "failed gate" in report.rationale.lower() or "regressed" in report.rationale.lower()


class TestMLOpsPipelineOrchestrator:
    """Verify master pipeline orchestration execution."""

    def test_dry_run_pipeline_demand(self):
        summary = run_pipeline(domains=["demand"], force=True, dry_run=True)
        assert "demand" in summary
        assert summary["demand"]["status"] in ["DRY_RUN_PASSED", "PROMOTED_AND_DEPLOYED"]

    def test_full_pipeline_single_domain_demand(self):
        summary = run_pipeline(domains=["demand"], force=True, dry_run=False)
        assert "demand" in summary
        assert summary["demand"]["status"] == "PROMOTED_AND_DEPLOYED"
        assert "decisions_generated" in summary["demand"]
