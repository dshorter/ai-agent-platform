# Predictor Pipeline Integration Notes

**Date:** February 6, 2026
**Spec:** `predictor_ingest/docs/deployment/platform-integration-spec.md`
**Status:** Web UI live, pipeline container profile-gated

---

## What Was Implemented

### Docker Compose (`docker-compose.yml`)
- Predictor service defined with `profiles: ["predictor"]` — excluded from default deploy
- Build context: `../predictor_ingest` (sibling repo)
- Dockerfile: `../ai-agent-platform/predictor/Dockerfile`
- Named volume `predictor-data` for `/app/data`
- Environment: `TZ`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`

### Nginx (`nginx/nginx.conf`)
- `/predictor/` location block serves all static files including `data/graphs/`
- Alias points to `/srv/predictor/` (mounted from `predictor_ingest/web/`)
- `Cache-Control: no-cache` for fresh graph data

### Dockerfile (`predictor/Dockerfile`)
- Python 3.11-slim with gcc, libxml2, libxslt, sqlite3, cron, make
- Installs via `pip install -e .` (pyproject.toml, not requirements.txt)
- Initializes DB: `python scripts/init_db.py --db data/db/predictor.db --schema schemas/sqlite.sql`
- Cron: SQLite backup at 5:30 AM ET, pipeline at 6:00 AM ET
- Healthcheck: DB file exists + cron process running

### Safe-Reboot (`usr_local_sbin_safe-reboot.sh`)
- `wait_for_predictor_pipeline()` — waits up to 120s for `pipeline.lock` to clear
- `backup_predictor_db()` — SQLite `.backup` before shutdown, non-fatal on failure

### Health Checks (`usr_local_sbin_agent-platform-health.sh`)
- `check_predictor_health()` — container status, DB >1KB, backup freshness <48h

---

## Deviations from Original Spec

### 1. `pyproject.toml` instead of `requirements.txt`
- **Spec assumed:** `COPY requirements.txt` + `pip install -r requirements.txt`
- **Reality:** `predictor_ingest` uses modern Python packaging with `pyproject.toml`
- **Fix:** `COPY . .` then `pip install --no-cache-dir -e .`

### 2. No separate `public/graphs/` shared directory
- **Spec assumed:** Graph JSON output shared via a cross-repo directory mount
- **Reality:** Pipeline writes directly to `predictor_ingest/web/data/graphs/` and nginx serves the entire `web/` tree. Self-contained, no plumbing needed.
- **Removed:** `public/graphs/.gitkeep` and the `./public/graphs` volume mount

### 3. Nginx mount path is `/srv/predictor`, not nested under `/usr/share/nginx/html`
- **Spec assumed:** Mount into `/usr/share/nginx/html/predictor`
- **Reality:** `./public` is mounted read-only at `/usr/share/nginx/html`. Docker cannot create a sub-mountpoint inside a read-only volume.
- **Fix:** Mount to `/srv/predictor` and use nginx `alias` directive

### 4. ngrok `--domain` flag replaced with `--url`
- **Spec didn't mention this**, but discovered during implementation
- Newer ngrok versions deprecated `--domain`; the flag silently fails to create the tunnel
- Updated in `docker-compose.yml` and all docs

### 5. Predictor service gated behind Docker Compose profile
- **Spec assumed:** Predictor runs as part of the default stack
- **Reality:** `profiles: ["predictor"]` keeps it out of `docker compose up` by default
- **Reason:** CI/CD deploys via `docker compose pull && up -d`. The predictor requires a build step and the sibling repo, which aren't guaranteed in all environments.
- **To activate:** `docker compose --profile predictor build predictor && docker compose --profile predictor up -d`

### 6. `init_db.py` requires explicit flags
- **Spec assumed:** Default paths match
- **Reality:** `init_db.py` defaults to `data/db/ingest.sqlite`, but Makefile expects `data/db/predictor.db`
- **Fix:** Pass `--db data/db/predictor.db --schema schemas/sqlite.sql` explicitly

---

## Still Pending

### In `predictor_ingest` repo
- **Makefile lock file handling** — `touch pipeline.lock` before pipeline targets, `rm pipeline.lock` after. Required for safe-reboot awareness.

### In `ai-agent-platform` repo
- **API keys in `.env`** — `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` need to be added when the pipeline goes live
- **Predictor container first run** — `docker compose --profile predictor build predictor && docker compose --profile predictor up -d`

---

## Quick Reference

```bash
# Default deploy (no predictor)
docker compose up -d

# Enable predictor
docker compose --profile predictor build predictor
docker compose --profile predictor up -d

# Check predictor health
docker exec predictor-pipeline test -f /app/data/db/predictor.db && echo "DB OK"
docker exec predictor-pipeline pgrep cron && echo "Cron OK"

# Manual pipeline run
docker exec predictor-pipeline make ingest

# View predictor UI
curl https://agents-platform.ngrok.io/predictor/
```
