#!/bin/bash
# Postgres container init: creates the ai_agent_platform database
# alongside the default hvac_demo DB, then loads its schema.
#
# Runs only on first-boot of the postgres volume. For existing
# deployments, run the equivalent commands manually — see
# database/README.md.

set -e

psql -v ON_ERROR_STOP=1 \
     --username "$POSTGRES_USER" \
     --dbname postgres \
     <<-EOSQL
    CREATE DATABASE ai_agent_platform;
EOSQL

psql -v ON_ERROR_STOP=1 \
     --username "$POSTGRES_USER" \
     --dbname ai_agent_platform \
     -f /docker-entrypoint-initdb.d/ai_agent_platform_schema.sql
