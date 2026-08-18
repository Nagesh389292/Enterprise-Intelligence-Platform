# Terraform Infrastructure as Code (IaC) for AWS Enterprise Production Deployment

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# -----------------------------------------------------------------------------
# 1. Amazon ECR Private Repositories
# -----------------------------------------------------------------------------
resource "aws_ecr_repository" "api_repo" {
  name                 = "${var.app_name}-api"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "agent_repo" {
  name                 = "${var.app_name}-agent"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# -----------------------------------------------------------------------------
# 2. Amazon S3 Buckets (MLflow Artifacts & Parquet Data Lake)
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "mlflow_artifacts" {
  bucket        = "${var.app_name}-mlflow-artifacts-${var.environment}"
  force_destroy = false
}

resource "aws_s3_bucket_server_side_encryption_configuration" "mlflow_art_enc" {
  bucket = aws_s3_bucket.mlflow_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# -----------------------------------------------------------------------------
# 3. VPC & Subnet Networking Infrastructure
# -----------------------------------------------------------------------------
resource "aws_vpc" "main_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.app_name}-vpc"
  }
}

resource "aws_subnet" "public_1" {
  vpc_id                  = aws_vpc.main_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true
}

resource "aws_subnet" "private_1" {
  vpc_id            = aws_vpc.main_vpc.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "${var.aws_region}b"
}

# -----------------------------------------------------------------------------
# 4. Amazon RDS PostgreSQL Enterprise Database
# -----------------------------------------------------------------------------
resource "aws_db_subnet_group" "db_subnets" {
  name       = "${var.app_name}-db-subnets"
  subnet_ids = [aws_subnet.public_1.id, aws_subnet.private_1.id]
}

resource "aws_db_instance" "postgres_dw" {
  identifier             = "${var.app_name}-postgres"
  allocated_storage      = 100
  max_allocated_storage  = 500
  engine                 = "postgres"
  engine_version         = "15.4"
  instance_class         = "db.r6g.xlarge"
  db_name                = "nexacore_dw"
  username               = "nexacore_admin"
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.db_subnets.name
  skip_final_snapshot    = true
  storage_encrypted      = true
  multi_az               = true
}

# -----------------------------------------------------------------------------
# 5. Amazon ECS Fargate Cluster & Service
# -----------------------------------------------------------------------------
resource "aws_ecs_cluster" "ecs_cluster" {
  name = "${var.app_name}-cluster"
}

resource "aws_cloudwatch_log_group" "ecs_api_logs" {
  name              = "/ecs/${var.app_name}-api"
  retention_in_days = 30
}
