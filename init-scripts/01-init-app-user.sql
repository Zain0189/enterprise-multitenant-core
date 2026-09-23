-- 01-init-app-user.sql
-- Create non-superuser application role
-- PostgreSQL superusers automatically bypass RLS; app_user ensures strict policy enforcement.

DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user'
   ) THEN
      CREATE ROLE app_user WITH LOGIN PASSWORD 'apppassword';
   END IF;
END
$do$;

-- Grant connection permissions on the target database
GRANT CONNECT ON DATABASE enterprise_db TO app_user;

-- Ensure schema usage
\c enterprise_db;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
GRANT USAGE, CREATE ON SCHEMA public TO app_user;

-- Set default permissions for tables created in the future
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_user;