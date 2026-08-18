"""
scripts/run_stage8b.py
----------------------
Execution runner for Stage 8B Demand Forecasting ML notebook.
Converts percent script to .ipynb, executes end-to-end, embeds cell outputs,
and generates JSON validation report `docs/data_science/stage8b_execution_report.json`.
"""

import os
import sys
import time
import json
import jupytext
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def run_stage8b():
    print("=" * 80)
    print("EXECUTING STAGE 8B: DEMAND FORECASTING ML NOTEBOOK")
    print("=" * 80)

    os.makedirs("notebooks", exist_ok=True)
    os.makedirs("docs/data_science", exist_ok=True)

    py_script = "notebooks/08_stage8b_demand_forecasting_ml.py"
    ipynb_file = "notebooks/08_stage8b_demand_forecasting_ml.ipynb"
    report_file = "docs/data_science/stage8b_execution_report.json"

    # 1. Convert .py to .ipynb
    print(f"Reading {py_script}...")
    nb = jupytext.read(py_script)

    # 2. Execute Notebook
    print("Executing notebook end-to-end with ipykernel...")
    start_time = time.time()
    ep = ExecutePreprocessor(timeout=600, kernel_name="python3")

    try:
        ep.preprocess(nb, {"metadata": {"path": "."}})
        status = "PASS"
        error_msg = None
    except Exception as e:
        status = "FAIL"
        error_msg = str(e)
        print(f"FAILED to execute notebook: {e}")

    execution_time = round(time.time() - start_time, 2)

    # 3. Write executed notebook to disk
    with open(ipynb_file, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)

    print(f"Saved executed notebook to {ipynb_file} ({execution_time}s)")

    # 4. Generate JSON Report
    report = {
        "stage": "Stage 8B — Demand Forecasting ML Engineering",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "overall_status": status,
        "execution_time_seconds": execution_time,
        "notebook": ipynb_file,
        "error_message": error_msg,
        "artifacts_generated": [
            "models/demand/champion_demand_model.pkl",
            "models/demand/champion_metadata.json",
            "docs/data_science/demand_model_card.md",
            "docs/data_science/figures/demand_mape_model_comparison.png",
            "docs/data_science/figures/demand_actual_vs_predicted.png",
            "docs/data_science/figures/demand_shap_beeswarm.png"
        ]
    }

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Saved execution report to {report_file}")
    
    if status == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    run_stage8b()
