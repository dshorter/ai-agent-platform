# Database

The Postgres container hosts two databases on the same instance:

| Database | Purpose | Schema file |
|----------|---------|-------------|
| `hvac_demo` | HVAC digital twin test case (first platform tenant) | `hvac_schema.sql` |
| `ai_agent_platform` | Generic platform spine — all agent pipelines | `ai_agent_platform/001_init.sql` |

`hvac_demo` is created automatically by the Postgres image from the
`POSTGRES_DB` env var in `docker-compose.yml`. `ai_agent_platform` is
created by the init script in `init/` on first container boot.

## Fresh deployment

Nothing to do — bring up the stack with `docker-compose up -d` and both
databases are created and schematized on first boot.

## Existing deployment (volume already initialized)

The init script only runs on first boot. For existing Postgres volumes:

```bash
# Create the second database
docker exec -i hvac-postgres psql -U hvac_user -d postgres \
    -c "CREATE DATABASE ai_agent_platform;"

# Load the schema
docker exec -i hvac-postgres psql -U hvac_user -d ai_agent_platform \
    < database/ai_agent_platform/001_init.sql
```

## Connecting

```bash
# HVAC test case
docker exec -it hvac-postgres psql -U hvac_user -d hvac_demo

# Platform DB (default for the blog pipeline)
docker exec -it hvac-postgres psql -U hvac_user -d ai_agent_platform
```

The `POSTGRES_DSN` env var in pipeline configs defaults to
`postgresql://hvac_user@localhost:5432/ai_agent_platform`.
