# Data Generation Engine Architecture
### NexaCore Enterprise Intelligence Platform

---

## 1. Package Structure & Module Responsibilities

The generator is structured as a modular Python package located in `scripts/enterprise_data_generator/`:

```text
enterprise_data_generator/
│
├── config/                     # Configuration schemas & scale profiles
│   ├── __init__.py
│   ├── profiles.py             # Dev, Integration, & Scale profile YAML/dict loaders
│   └── settings.py             # Global constants & seed management
│
├── models/                     # Dataclasses & Pydantic entity domain schemas
│   ├── __init__.py
│   ├── customer.py             # Customer, Segment, Address schemas
│   ├── sales.py                # Product, Order, OrderItem schemas
│   ├── supply_chain.py         # Supplier, Warehouse, Inventory schemas
│   ├── operations.py           # Machine, Telemetry, Maintenance, Failure schemas
│   └── support.py              # SupportTicket, Interaction, CSAT schemas
│
├── generators/                 # Pure domain entity generator modules
│   ├── __init__.py
│   ├── base.py                 # Abstract Base Generator class
│   ├── customer_generator.py   # Customer domain generation logic
│   ├── product_generator.py    # Product & catalog generation logic
│   ├── order_generator.py      # Sales order & line-item generation logic
│   ├── inventory_generator.py  # Warehouse inventory & stock movement logic
│   ├── iot_generator.py        # High-frequency telemetry & anomaly streamer
│   └── support_generator.py    # Support ticket & CSAT score logic
│
├── scenarios/                  # Business behavior & temporal scenario engines
│   ├── __init__.py
│   ├── seasonality.py          # Holiday, promotional, and monthly demand curves
│   ├── churn_behavior.py       # Customer engagement decay & churn scenario
│   └── degradation.py          # Machine wear, overheating & failure scenario
│
├── corruption/                 # Controlled data quality corruption layer
│   ├── __init__.py
│   ├── corruptor.py            # Main corruption orchestrator
│   └── rules.py                # Null injection, duplicate key, schema drift rules
│
├── writers/                    # Decoupled persistence output adapters
│   ├── __init__.py
│   ├── base_writer.py          # Abstract Writer interface
│   ├── csv_writer.py           # Multi-file CSV output writer
│   ├── parquet_writer.py       # Partitioned Parquet lakehouse writer
│   └── postgres_writer.py      # Direct PostgreSQL batch insertion writer
│
├── validation/                 # Post-generation relational integrity checkers
│   ├── __init__.py
│   └── integrity_checker.py    # Foreign key & constraint validator
│
└── cli.py                      # CLI entrypoint parser (Click / argparse)
```

---

## 2. Decoupled Persistence Interface Design

To separate **Data Generation** from **Data Storage**, all persistence logic is abstracted via `BaseWriter`:

```text
                   ┌───────────────────────┐
                   │ Entity Generator DAG  │
                   └───────────┬───────────┘
                               │
                               ▼
                   ┌───────────────────────┐
                   │    Abstract Writer    │
                   └───────────┬───────────┘
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   CSV Writer    │   │ Parquet Writer  │   │ Postgres Writer │
│(data/raw/*.csv) │   │(data/raw/*.pq)  │   │ (Direct DB ETL) │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

---

## 3. Seed-Based Deterministic Reproducibility

* **Global Random Seeding**: All random number generators (`random`, `numpy.random`, `Faker`) are seeded globally using a configurable integer seed (e.g., `seed=42`).
* **Guaranteed Idempotency**: Re-running the generator with identical arguments and seed produces bit-for-bit identical records, ensuring full test reproducibility.
