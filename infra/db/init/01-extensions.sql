-- Extensions required by Mahalli Pro. Runs once on a fresh Postgres volume.
CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector: RAG embeddings (Module 9)
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- fuzzy vendor / commodity name matching
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid(), crypto helpers

-- Non-superuser application role. RLS policies are ENFORCED for this role.
-- The superuser (mahalli_admin) bypasses RLS and is used only by the
-- Master Admin control center / ghost-login path.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mahalli_app') THEN
    CREATE ROLE mahalli_app LOGIN PASSWORD 'app_pw';
  END IF;
END$$;
GRANT ALL ON SCHEMA public TO mahalli_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO mahalli_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO mahalli_app;
