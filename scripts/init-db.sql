-- Initialize GovCon AI Pipeline Database
-- This script runs on container startup

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search
CREATE EXTENSION IF NOT EXISTS "btree_gin";  -- For GIN indexes

-- Create custom types (will be created by SQLAlchemy, but here for reference)

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE govcon TO bronze;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bronze;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bronze;

-- Create indexes for performance
-- (SQLAlchemy will create tables, we can add indexes via migrations later)
