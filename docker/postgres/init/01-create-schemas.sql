-- ==============================================================================
-- Enterprise Intelligence Platform — Database Initialization Script 01
-- Description: Creates database schemas (source, analytics, staging, audit)
-- ==============================================================================

-- Enable UUID Extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create Core Platform Schemas
CREATE SCHEMA IF NOT EXISTS source;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set default search path
SET search_path TO source, analytics, staging, audit, public;
