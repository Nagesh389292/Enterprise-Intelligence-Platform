# Database Infrastructure & Operations Manual
### NexaCore Enterprise Intelligence Platform

---

## 📌 Architectural Overview

The **Enterprise Intelligence Platform (EIP)** database layer is built on **PostgreSQL 15+** running in a containerized Docker environment. It is logically partitioned into four distinct schemas to preserve domain boundaries, auditability, and analytical query performance:

```text
               PostgreSQL Database (nexacore_dw)
                               │
       ┌───────────────────────┼───────────────────────┬───────────────────────┐
       ▼                       ▼                       ▼                       ▼
┌──────────────┐        ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│    source    │        │   staging    │        │  analytics   │        │    audit     │
├──────────────┤        ├──────────────┤        ├──────────────┤        ├──────────────┤
│ 18 3NF Tables│        │ Intermediate │        │ 6 Dimensions │        │ Pipeline & DQ│
│ (Raw Events &│        │ Pipeline     │        │ 6 Star Facts │        │ Quarantine   │
│  Entities)   │        │ Buffer       │        │ (Gold Layer) │        │ Audit Logs   │
└──────────────┘        └──────────────┘        └──────────────┘        └──────────────┘
```

---

## 📂 Database Directory Layout

```text
docs/database/
├── README.md               # Main database hub documentation & CLI command reference
├── schema-overview.md      # Detailed documentation for source, analytics, staging, & audit schemas
├── migration-guide.md      # Deterministic migration, startup, reset, & verification guide
└── indexing-strategy.md   # Indexing design rationales for performance tuning

docker/postgres/init/
├── 01-create-schemas.sql   # Creates source, analytics, staging, & audit schemas + UUID extension
├── 02-source-schema.sql    # DDL for 18 normalized 3NF source system tables
├── 03-analytics-schema.sql # DDL for 12 Gold dimensional star schema tables (dim & fact)
├── 04-audit-schema.sql     # DDL for pipeline execution, data quality, & quarantine logs
└── 05-create-indexes.sql   # Performance B-Tree indexes for foreign keys & timestamp filters
```

---

## 🛠️ Quick Management CLI Commands

### 1. Start PostgreSQL Service
```bash
docker-compose up -d postgres
```

### 2. Connect via psql CLI
```bash
docker exec -it nexacore_postgres psql -U nexacore_admin -d nexacore_dw
```

### 3. Check Schemas & Tables
```sql
\dn                             -- List database schemas
\dt source.*                    -- List normalized source system tables
\dt analytics.*                 -- List gold star-schema tables
\dt audit.*                     -- List audit infrastructure tables
```

### 4. Run Schema Verification Test Suite
```bash
pytest tests/test_database_schema.py -v
```
