-- Auto-creates the dedicated `litellm` database that the LiteLLM proxy uses for its
-- metadata (virtual keys, spend logs). Runs only on a fresh Postgres data volume via
-- /docker-entrypoint-initdb.d. Idempotent guard so re-runs are harmless.
SELECT 'CREATE DATABASE litellm'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'litellm')\gexec
