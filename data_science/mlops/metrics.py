"""
data_science/mlops/metrics.py
==============================
Stage 12 — Prometheus Metrics Exporter & Observability Module

Exposes Prometheus counters, gauges, and histograms for:
  - API HTTP request counts, status codes, and latency distributions
  - Model prediction distributions and inference latency
  - Feature and prediction drift alerts
  - MLOps retraining and champion-challenger promotion events
  - Stage 10 Multi-Agent decision verdicts and risk distributions
"""

import time
from typing import Callable
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# 1. API HTTP Metrics
HTTP_REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status_code"]
)

HTTP_REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"]
)

# 2. Model Inference & Drift Metrics
MODEL_PREDICTIONS_TOTAL = Counter(
    "model_predictions_total",
    "Total model predictions generated",
    ["domain", "model_version"]
)

MODEL_DRIFT_ALERT_COUNT = Counter(
    "model_drift_alerts_total",
    "Total data or prediction drift alerts triggered",
    ["domain"]
)

MODEL_RETRAIN_EVENT_COUNT = Counter(
    "model_retrain_events_total",
    "Total model retraining pipeline executions",
    ["domain", "status"]
)

# 3. Agent Decision Intelligence Metrics
AGENT_DECISION_TOTAL = Counter(
    "agent_decisions_total",
    "Total structured agent decisions persisted",
    ["domain", "final_verdict", "risk_level"]
)

ACTIVE_MODEL_VERSION = Gauge(
    "active_model_version",
    "Active production model version indicator",
    ["domain", "model_name"]
)

def record_http_metrics(method: str, endpoint: str, status_code: int, duration: float):
    """Record HTTP request counter and latency metric."""
    HTTP_REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()
    HTTP_REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)

def record_agent_decision(domain: str, verdict: str, risk_level: str):
    """Record an AgentBus decision output."""
    AGENT_DECISION_TOTAL.labels(domain=domain, final_verdict=verdict, risk_level=risk_level).inc()

def get_metrics_response():
    """Return raw Prometheus metrics text response."""
    return generate_latest(), CONTENT_TYPE_LATEST
