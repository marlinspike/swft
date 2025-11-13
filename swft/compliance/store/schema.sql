-- Convenience wrapper to apply the full schema with psql:
--   psql "dbname=..." -f swft/compliance/store/schema.sql
\i './migrations/0001_initial.sql'
\i './migrations/0002_run_evidence.sql'
