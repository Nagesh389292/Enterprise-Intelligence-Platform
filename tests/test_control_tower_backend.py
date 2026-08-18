"""
tests/test_control_tower_backend.py
====================================
Stage 13 — Enterprise Intelligence Control Tower Integration Test Suite

Tests:
  - Executive Overview Summary API (/api/control-tower/summary)
  - Customer Intelligence API (/api/control-tower/customer)
  - Demand Intelligence API (/api/control-tower/demand)
  - Inventory Intelligence API (/api/control-tower/inventory)
  - Machine Operations API (/api/control-tower/operations)
  - Multi-Agent Decisions Audit Trail API (/api/control-tower/decisions)
"""

import pytest
from fastapi.testclient import TestClient
from data_science.mlops.serving_api import app

client = TestClient(app)

class TestControlTowerEndpoints:
    def test_summary_endpoint_returns_200(self):
        response = client.get("/api/control-tower/summary")
        assert response.status_code == 200
        data = response.json()
        assert "executive_kpis" in data
        assert "active_models" in data
        assert data["executive_kpis"]["system_health"] == "OPERATIONAL"

    def test_customer_endpoint_returns_records(self):
        response = client.get("/api/control-tower/customer")
        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "customer"
        assert len(data["top_at_risk_customers"]) > 0

    def test_demand_endpoint_returns_forecasts(self):
        response = client.get("/api/control-tower/demand")
        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "demand"
        assert len(data["demand_forecasts"]) > 0

    def test_inventory_endpoint_returns_alerts(self):
        response = client.get("/api/control-tower/inventory")
        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "inventory"
        assert len(data["stockout_alerts"]) > 0

    def test_operations_endpoint_returns_machine_health(self):
        response = client.get("/api/control-tower/operations")
        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "operations"
        assert len(data["machine_health"]) > 0

    def test_decisions_endpoint_returns_agentbus_records(self):
        response = client.get("/api/control-tower/decisions")
        assert response.status_code == 200
        data = response.json()
        assert "total_records" in data
        assert len(data["decisions"]) > 0
        first_dec = data["decisions"][0]
        assert "decision_id" in first_dec
        assert "final_verdict" in first_dec

    def test_mlops_endpoint_returns_model_health(self):
        response = client.get("/api/control-tower/mlops")
        assert response.status_code == 200
        data = response.json()
        assert "total_models" in data
        assert data["total_models"] == 4
        assert len(data["models"]) == 4

