# Enterprise Intelligence Platform — AWS Cloud Architecture Specification

## Overview

The Enterprise Intelligence Platform is designed to run natively on Amazon Web Services (AWS) using managed container orchestration, relational database services, scalable object storage, and automated monitoring.

```text
                                  AWS ARCHITECTURE

                               ┌──────────────────────┐
                               │  AWS Route53 / ALB   │
                               └──────────┬───────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │  Amazon ECS Fargate  │
                               │   (Public Subnets)   │
                               └──────────┬───────────┘
                                          │
                  ┌───────────────────────┼───────────────────────┐
                  ▼                       ▼                       ▼
       ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
       │ FastAPI Scoring API │ │  AgentBus Service   │ │   MLflow Server     │
       └──────────┬──────────┘ └──────────┬──────────┘ └──────────┬──────────┘
                  │                       │                       │
                  ▼                       ▼                       ▼
       ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
       │ Amazon RDS Postgres │ │ Amazon S3 Buckets   │ │ Amazon CloudWatch   │
       │ (Multi-AZ DW)       │ │ (Data Lake/Artifact)│ │ (Logs & Alarms)     │
       └─────────────────────┘ └─────────────────────┘ └─────────────────────┘
```

---

## Managed AWS Services Specification

| AWS Service | Production Purpose | Sizing / Spec |
| :--- | :--- | :--- |
| **Amazon ECS Fargate** | Serverless container execution for FastAPI scoring API, AgentBus decision service, and MLflow | 2 vCPU, 4GB RAM per container task |
| **Amazon ECR** | Private Docker container image registry for API & Agent images | Multi-region, immutable image tags, Trivy security scanning |
| **Amazon RDS PostgreSQL** | Production Enterprise Data Warehouse storing 3NF source, Gold star-schema, and agent decision tables | `db.r6g.xlarge` Multi-AZ deployment, PostgreSQL 15, encrypted storage |
| **Amazon S3** | Object storage for raw Parquet data lake, dbt artifacts, and MLflow model registry artifacts | S3 Standard with Lifecycle rules (Standard-IA after 30d) |
| **AWS ALB** | Application Load Balancer distributing external HTTPS traffic across ECS tasks | TLS 1.3 termination, Health checks on `/healthz` |
| **Amazon CloudWatch** | Centralized logging, container metrics, latency alarms, and drift notifications | CloudWatch Logs Insights + SNS alerts on 5xx errors |

---

## Networking & Security

- **VPC Topology**: 2 Public Subnets (ALB, NAT Gateways) + 2 Private Subnets (ECS Tasks, RDS, MLflow).
- **Security Groups**:
  - `alb-sg`: Permits inbound HTTPS (443) from 0.0.0.0/0.
  - `ecs-sg`: Permits inbound HTTP (8000) *only* from `alb-sg`.
  - `db-sg`: Permits inbound PostgreSQL (5432) *only* from `ecs-sg`.
- **IAM Roles**: ECS Task Execution Role with KMS decrypt, Secrets Manager access (`POSTGRES_PASSWORD`, `API_KEY`), and S3 bucket read/write permissions.
