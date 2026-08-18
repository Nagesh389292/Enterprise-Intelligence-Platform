"""
tests/test_deployment_hardening.py
===================================
Stage 12 — Enterprise Production Deployment & API Hardening Test Suite

Tests:
  - Liveness (/healthz) and Readiness (/ready) probes
  - API Key Security Middleware (401 Unauthorized vs 200 OK)
  - Model Version Audit endpoint (/models/version)
  - Prometheus Metrics Exporter (/metrics)
  - RFC 7807 Error Contract Compliance
"""

import os
import pytest
from fastapi.testclient import TestClient

from data_science.mlops.serving_api import app, API_KEY_SECRET
from data_science.mlops.metrics import record_http_metrics, record_agent_decision

client = TestClient(app)

class TestLivenessAndReadinessProbes:
    def test_healthz_liveness_returns_200(self):
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data

    def test_ready_readiness_returns_200(self):
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["db_connected"] is True
        assert data["models_available"] is True

class TestModelVersionAuditEndpoint:
    def test_models_version_returns_artifact_metadata(self):
        response = client.get("/models/version")
        assert response.status_code == 200
        data = response.json()
        assert "churn" in data
        assert "demand" in data
        assert "stockout" in data

class TestPrometheusMetricsEndpoint:
    def test_metrics_endpoint_returns_prometheus_format(self):
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "http_requests_total" in response.text or "# HELP" in response.text

    def test_record_agent_decision_metric(self):
        record_agent_decision(domain="churn", verdict="APPROVED", risk_level="Low Risk")
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "agent_decisions_total" in response.text

class TestAPIKeySecurityMiddleware:
    def test_unauthenticated_request_returns_401(self, monkeypatch):
        monkeypatch.setenv("BYPASS_AUTH", "false")
        payload = {
            "customer_id": "CUST_999",
            "tenure_months": 12.0,
            "total_orders": 5,
            "total_spend": 500.0,
            "avg_order_value": 100.0,
            "avg_csat_score": 4.5,
            "days_since_last_order": 10.0
        }
        # Request without header
        response = client.post("/predict/churn", json=payload)
        assert response.status_code == 401
        err = response.json()["detail"]
        assert err["status"] == 401
        assert "Invalid or Missing API Key" in err["title"]

    def test_authenticated_request_with_api_key_succeeds(self, monkeypatch):
        monkeypatch.setenv("BYPASS_AUTH", "false")
        payload = {
            "customer_id": "CUST_999",
            "tenure_months": 12.0,
            "total_orders": 5,
            "total_spend": 500.0,
            "avg_order_value": 100.0,
            "avg_csat_score": 4.5,
            "days_since_last_order": 10.0
        }
        headers = {"X-API-Key": API_KEY_SECRET}
        response = client.post("/predict/churn", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["customer_id"] == "CUST_999"
        assert "churn_probability" in data
