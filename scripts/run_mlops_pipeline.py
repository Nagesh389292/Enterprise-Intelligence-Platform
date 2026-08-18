"""
scripts/run_mlops_pipeline.py
==============================
Stage 11 — Master Production MLOps & CI/CD Pipeline Orchestrator

Orchestrates the complete lifecycle:
  Drift Monitoring -> Domain-Aware Retraining -> Champion-Challenger Gating ->
  MLflow Promotion -> Batch Inference -> Stage 10 Decision Intelligence

Usage:
  python scripts/run_mlops_pipeline.py [--domain <domain>] [--force] [--dry-run]
"""

import sys
import os
import argparse
import logging
import shutil
import joblib
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from data_science.mlops.drift_detector import DriftDetector
from data_science.mlops.retrain import DomainRetrainer, VALID_DOMAINS
from data_science.mlops.evaluator import ModelEvaluator
from data_science.mlops.registry import ModelRegistryManager
from data_science.mlops.batch_inference import BatchInferenceEngine
from data_science.agents.agent_bus import AgentBus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("mlops_pipeline")

CHAMPION_PATHS = {
    "churn":          "models/churn/champion_churn_model.pkl",
    "demand":         "models/demand/champion_demand_model.pkl",
    "stockout":       "models/inventory/champion_stockout_model.pkl",
    "machine_health": "models/telemetry/champion_failure_model.pkl",
}

def run_pipeline(domains: list, force: bool = False, dry_run: bool = False):
    """
    Run end-to-end MLOps pipeline for specified domains.
    """
    logger.info("=" * 80)
    logger.info("ENTERPRISE MLOPS CI/CD PIPELINE ORCHESTRATOR")
    logger.info("Target Domains: %s | Force Retrain: %s | Dry Run: %s", domains, force, dry_run)
    logger.info("=" * 80)

    monitor = DriftDetector()
    retrainer = DomainRetrainer()
    evaluator = ModelEvaluator()
    registry = ModelRegistryManager()
    batch_engine = BatchInferenceEngine()

    pipeline_summary = {}

    for domain in domains:
        logger.info("\n>>> Processing Domain: %s <<<", domain.upper())

        # 1. Check Drift Status
        drift_report = monitor.detect_domain_drift(domain)
        has_drift = drift_report.get("has_drift", False)
        logger.info("Drift Status for %s: has_drift=%s (PSI_max=%.4f)",
                    domain, has_drift, drift_report.get("max_psi", 0.0))

        if not has_drift and not force:
            logger.info("No drift detected for domain '%s' and force flag not set. Skipping retraining.", domain)
            pipeline_summary[domain] = {"status": "SKIPPED", "reason": "No drift detected"}
            continue

        # 2. Execute Targeted Retraining
        retrain_result = retrainer.retrain_domain(domain)
        candidate_path = retrain_result["candidate_path"]
        candidate_run_id = retrain_result["mlflow_run_id"]

        logger.info("Candidate model trained for %s: %s (MLflow Run ID: %s)",
                    domain, candidate_path, candidate_run_id)

        # 3. Champion vs. Challenger Evaluation & Gating
        eval_report = evaluator.evaluate_and_gate(domain, candidate_path)
        logger.info("Evaluation Gating Result for %s: PASSED=%s", domain, eval_report.passed_gate)
        logger.info("Rationale: %s", eval_report.rationale)

        if not eval_report.passed_gate:
            logger.warning("REJECTED: Candidate model failed promotion gate for %s. Keeping Production champion.", domain)
            pipeline_summary[domain] = {
                "status": "REJECTED",
                "rationale": eval_report.rationale,
                "candidate_metrics": eval_report.candidate_metrics,
                "champion_metrics": eval_report.champion_metrics,
            }
            continue

        if dry_run:
            logger.info("DRY RUN MODE: Promotion gate PASSED for %s, but skipping artifact overwrite & inference.", domain)
            pipeline_summary[domain] = {"status": "DRY_RUN_PASSED", "rationale": eval_report.rationale}
            continue

        # 4. Promotion & Artifact Overwrite
        logger.info("PROMOTING candidate model to Production for domain '%s'...", domain)

        champion_dst = CHAMPION_PATHS.get(domain)
        if champion_dst:
            os.makedirs(os.path.dirname(champion_dst), exist_ok=True)
            shutil.copy2(candidate_path, champion_dst)
            logger.info("Overwrote champion artifact: %s", champion_dst)

        # Promote alias in MLflow
        model_name = f"candidate_{domain}_model"
        candidate_version = retrain_result.get("version", "1")
        try:
            registry.promote_model_stage(model_name, version=str(candidate_version), stage="Production")
            logger.info("Promoted MLflow model '%s' v%s to Production stage/alias", model_name, candidate_version)
        except Exception as exc:
            logger.warning("MLflow promotion note: %s", exc)

        # 5. Refresh Batch Inference
        logger.info("Refreshing batch predictions for domain '%s'...", domain)
        if domain == "churn":
            inf_res = batch_engine.run_churn_batch_inference()
        elif domain == "demand":
            inf_res = batch_engine.run_demand_batch_inference()
        elif domain == "stockout":
            inf_res = batch_engine.run_stockout_batch_inference()
        elif domain == "machine_health":
            inf_res = batch_engine.run_machine_health_batch_inference()
        
        logger.info("Batch inference complete for %s: %s", domain, inf_res)

        # 6. Re-trigger Stage 10 Decision Intelligence
        logger.info("Re-triggering Stage 10 Multi-Agent Decision Bus...")
        bus = AgentBus()
        agent_decisions = bus.run()
        logger.info("Stage 10 AgentBus executed: %d decisions generated and persisted.", len(agent_decisions))

        pipeline_summary[domain] = {
            "status": "PROMOTED_AND_DEPLOYED",
            "rationale": eval_report.rationale,
            "candidate_metrics": eval_report.candidate_metrics,
            "decisions_generated": len(agent_decisions),
        }

    logger.info("\n" + "=" * 80)
    logger.info("MLOPS PIPELINE EXECUTION SUMMARY:")
    for d, s in pipeline_summary.items():
        logger.info("  - %-15s : %s", d, s)
    logger.info("=" * 80)
    return pipeline_summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Master MLOps CI/CD Pipeline Orchestrator")
    parser.add_argument("--domain", type=str, default="all", choices=VALID_DOMAINS + ["all"],
                        help="Specific domain to process or 'all'")
    parser.add_argument("--force", action="store_true", help="Force retraining even if no drift detected")
    parser.add_argument("--dry-run", action="store_true", help="Evaluate candidate without overwriting production champion")

    args = parser.parse_args()
    target_domains = VALID_DOMAINS if args.domain == "all" else [args.domain]
    run_pipeline(target_domains, force=args.force, dry_run=args.dry_run)
