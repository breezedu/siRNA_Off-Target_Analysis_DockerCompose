-- Initial database setup
-- This runs automatically when the PostgreSQL container starts

-- Enable extensions if needed
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create indexes for text search (optional, for advanced queries)
-- These will be created by SQLAlchemy models, but can be added here for reference

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE sirna_offtarget TO sirna_user;
 
