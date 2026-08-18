"""
CLI Execution Script: Data & Prediction Drift Monitoring Audit
===============================================================
Executes statistical feature drift (KS-Test, PSI) and prediction drift audits,
exporting structured audit report docs/mlops/drift_report.json.
"""

import sys
import os
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_science.mlops.drift_detector import DriftDetector

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    logger.info("Executing Data & Prediction Drift Audit...")
    detector = DriftDetector()
    results = detector.run_drift_audit()

    print("\n================================================================================")
    print("DRIFT MONITORING AUDIT SUMMARY")
    print("================================================================================")
    for domain, res in results.get("domains", {}).items():
        status_str = res.get("status")
        drifted = res.get("drifted_features_count", 0)
        retrain = res.get("retraining_recommended", False)
        print(f"  - Domain: {domain:<18} | Status: {status_str:<10} | Drifted Features: {drifted} | Retrain Triggered: {retrain}")
    print("================================================================================")
    print("Detailed report exported to: docs/mlops/drift_report.json")

if __name__ == "__main__":
    main()
