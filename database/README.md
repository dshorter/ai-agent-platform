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

## Migrations

`ai_agent_platform/NNN_*.sql` are applied in order and each is one transaction.
The first three are the initial schema; 004 and 005 built `scout_jewel` and its
provenance columns. Apply one by hand:

```bash
docker exec -i hvac-postgres psql -v ON_ERROR_STOP=1 -U hvac_user \
    -d ai_agent_platform < database/ai_agent_platform/004_scout_jewel.sql
```

**006 is different, and is NOT applied.** It creates the leads ledger's tables
and the grant that makes the pineapple rule a permission (ADR-003). Nothing in
the crew reads those tables — `pipelines/scout/state/leads.yaml` is still the
ledger — so applying it changes no behaviour, and it ships with the pieces a
change to this cluster needs, because there is no per-table restore point here:

| file | what it is |
|---|---|
| `006_scout_lead.sql` | the migration, one transaction |
| `006_verify.sql` | 12 assertions, in a transaction that always rolls back — including reading the privilege wall from behind it with `SET ROLE` |
| `006_rollback.sql` | a precise DROP of exactly what 006 creates. **Not** a dump reload: restoring a dump to undo a migration destroys everything written since it was taken |
| `apply-006-scout-lead.sh` | dump (outside this repo — it holds transcript-derived rows and origin is public), apply, verify, and tear the migration back out if verification fails |

```bash
./database/ai_agent_platform/apply-006-scout-lead.sh --check     # touches nothing
./database/ai_agent_platform/apply-006-scout-lead.sh             # dump, apply, verify
./database/ai_agent_platform/apply-006-scout-lead.sh --rollback  # deliberate teardown
```
