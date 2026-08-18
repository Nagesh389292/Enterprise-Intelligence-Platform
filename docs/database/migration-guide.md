# Database Initialization, Migration & Reproduction Guide
### NexaCore Enterprise Intelligence Platform

This document outlines the step-by-step procedure to initialize, migrate, verify, and cleanly reset the local PostgreSQL database environment.

---

## 1. Prerequisites & Developer Environment Setup

### 1.1 Local Software Requirements
* **Docker & Docker Desktop**: Installed and running on host OS.
* **Python**: Python 3.10+ installed.

### 1.2 Virtual Environment & Dependencies Setup (Windows PowerShell)
```powershell
# 1. Navigate to project root
cd enterprise-intelligence-platform

# 2. Create Python virtual environment (if not already created)
python -m venv venv

# 3. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 4. Install project dependencies
pip install -r requirements.txt
```

---

## 2. Step-by-Step Initialization & Verification Procedure

### Step 1: Launch PostgreSQL Container via Docker Compose
Launch the containerized PostgreSQL service (configured on host port `5433` to prevent collision with local PostgreSQL services):
```powershell
docker compose up -d postgres
```

The service executes initialization scripts in numerical sequence from `docker/postgres/init/`:
1. `01-create-schemas.sql` — Creates `source`, `analytics`, `staging`, `audit` schemas and enables `uuid-ossp` and `pgcrypto` extensions.
2. `02-source-schema.sql` — Creates 21 normalized 3NF source tables.
3. `03-analytics-schema.sql` — Creates 12 Gold dimensional star schema tables.
4. `04-audit-schema.sql` — Creates audit and quarantine tracking tables.
5. `05-create-indexes.sql` — Builds 37 targeted B-tree performance indexes.

### Step 2: Verify Container Health
```powershell
docker compose ps
```
Ensure status indicates `Up (healthy)`.

### Step 3: Run Static DDL Migration Script Validator
```powershell
python scripts/validate_sql_ddl.py
```

### Step 4: Run Live Database Runtime Schema Verification Tests
Run the automated pytest test suite (isolated via `pytest.ini` using `-p no:langsmith`):
```powershell
python -m pytest tests/test_database_schema.py -v
```

---

## 3. Database Reset Procedure (Clean Environment Reproduction)

To completely destroy the database volume and rebuild the schema from scratch:

```powershell
# 1. Stop containers and remove PostgreSQL data volume
docker compose down -v

# 2. Re-launch PostgreSQL container (triggers fresh init execution)
docker compose up -d postgres

# 3. Run runtime schema tests
python -m pytest tests/test_database_schema.py -v
```
