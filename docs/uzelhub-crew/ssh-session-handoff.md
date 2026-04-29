# SSH Session Handoff — Sprint Zero Go-Live

> **Purpose:** Pick up Sprint Zero work on the Hetzner VPS where the cloud session left off.
> **Prereq:** PR 1 (`claude/uzelhub-crew-sprint-zero`) and PR 2 (`claude/crew-db-and-cleanup`) merged to `main`.

---

## Where the cloud session left things

**Authored on `main` (after both PRs merge):**
- `agents/` — Content (Sonnet) and Marketer (Sonnet + Haiku) subagent definitions
- `pipelines/blog_pipeline/` — git reader, commit batcher, Ghost publisher, sequence-aware logging, cohesion graph helpers, runner
- `database/ai_agent_platform/001_init.sql` — generic platform schema
- `database/init/10_create_ai_agent_platform.sh` — first-boot DB creation hook (only runs on fresh Postgres volumes — see migration step below)
- `docker-compose.yml` — n8n stripped, init scripts mounted, Postgres + nginx + ngrok + (profile) predictor remain
- `pyproject.toml` — `anthropic`, `claude-agent-sdk`, `psycopg`, `httpx`, `pyjwt`, `python-slugify`, `python-json-logger`
- `scripts/run_blog_pipeline.sh` — cron wrapper

**Validated in the cloud session:**
- All modules parse
- `GitReader` + `CommitBatcher` smoke-tested against this repo's own history (10 commits → 2 kept → 1 batch)
- No live LLM calls, DB writes, or Ghost POSTs yet — that's the SSH session's job

**Not yet done:**
- DB migration on the existing Postgres volume (the init hook only runs on fresh volumes)
- Python package install on the VPS
- `predictor_ingest` path identification
- Ghost Admin API key setup
- First dry run, then first live single-batch run
- Director review of the first draft in Ghost admin

---

## SSH session checklist

### 1. Pull main and confirm state

```bash
ssh hetzner
cd /srv/ai-agent-platform   # adjust if path differs
git pull origin main
git log --oneline -5         # should show both PR 1 and PR 2 merge commits
```

**Verify:** `agents/` and `pipelines/blog_pipeline/` directories exist, `database/ai_agent_platform/001_init.sql` is present.

### 2. Create the new database in the existing Postgres volume

The Docker init script only fires on first boot. The existing volume already initialized for HVAC, so run the migration manually:

```bash
docker exec -i hvac-postgres psql -U hvac_user -d postgres \
    -c "CREATE DATABASE ai_agent_platform;"

docker exec -i hvac-postgres psql -U hvac_user -d ai_agent_platform \
    < database/ai_agent_platform/001_init.sql
```

**Verify:**
```bash
docker exec -it hvac-postgres psql -U hvac_user -d ai_agent_platform -c "\dt"
# Should list: pipeline_runs, pipeline_inputs, agent_decisions, posts, business_metrics, schema_version
```

### 3. Install the Python package

```bash
# Option A: system-wide
pip install -e .

# Option B: virtualenv (recommended on the VPS)
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

**Verify:**
```bash
python -c "from pipelines.blog_pipeline.runner import main; print('imports OK')"
```

### 4. Locate predictor_ingest and confirm it's a git repo

```bash
# Likely at /srv/predictor_ingest or similar — check existing setup
ls /srv/predictor_ingest/.git/HEAD
# If it's not there, clone it:
# git clone https://github.com/dshorter/predictor_ingest.git /srv/predictor_ingest
```

### 5. Set up environment

Create `/srv/ai-agent-platform/.env` (gitignored — never commit):

```bash
# Anthropic API
ANTHROPIC_API_KEY=sk-ant-...

# Ghost Admin API — get from Ghost admin UI:
#   Settings → Integrations → Add custom integration → copy "Admin API Key"
GHOST_ADMIN_URL=http://localhost:2368
GHOST_ADMIN_API_KEY=<key_id>:<secret_hex>

# Postgres
POSTGRES_DSN=postgresql://hvac_user:${POSTGRES_PASSWORD}@localhost:5432/ai_agent_platform

# Source repo
PIPELINE_SOURCE_REPO=/srv/predictor_ingest
PIPELINE_SOURCE_NAME=predictor_ingest
PIPELINE_PROJECT_CONTEXT="predictor_ingest — RSS/signal pipeline feeding the predictor."
```

```bash
chmod 600 .env
```

### 6. Dry run

No LLM, no DB, no Ghost — just verify the reader and batcher see real predictor_ingest commits.

```bash
set -a && source .env && set +a
python -m pipelines.blog_pipeline.runner --dry-run
```

**Expected output:** lines like
```
[dry-run] batch <sha>..<sha> (N commits, M lines)
```

If you see ~20–50 batches across the full predictor_ingest history, the reader and triviality filter are working.

**If batches look wrong:**
- Too few — triviality filter too aggressive. Check `pipelines/blog_pipeline/commit_batcher.py:TRIVIAL_SUBJECT_PATTERNS` and `TRIVIAL_MAX_LINES`.
- Too many tiny batches — file-overlap heuristic too strict. Loosen by widening `DEFAULT_WINDOW` or relaxing the overlap check.
- Reader errors — confirm `PIPELINE_SOURCE_REPO` is a real git working copy, not a bare clone.

### 7. First live run — single batch only

Before unleashing the full backlog crawl, cap the run to one batch to validate the LLM → Ghost path end-to-end.

```bash
python -m pipelines.blog_pipeline.runner --max-batches 1
```

`--max-batches N` is a built-in CLI flag — same one you'll reach for later if you ever need to recover from a partial failure or rerun a specific window.

**Verify:**
- One row in `pipeline_runs` with `status='success'`
- One row in `pipeline_inputs` with the commit batch
- 3+ rows in `agent_decisions` (content_agent, marketer_agent.extract, marketer_agent.package, ghost.create_draft)
- One draft visible in Ghost admin under `/ghost/#/posts/?type=drafts`

```bash
docker exec -it hvac-postgres psql -U hvac_user -d ai_agent_platform <<'SQL'
SELECT pipeline_name, status, duration_ms, started_at FROM pipeline_runs ORDER BY started_at DESC LIMIT 5;
SELECT agent_name, llm_model, token_count_input, token_count_output, processing_time_ms
  FROM agent_decisions ORDER BY decision_timestamp DESC LIMIT 10;
SQL
```

### 8. Director review the first draft

Open Ghost admin in a browser, find the draft, read it.

**What to evaluate:**
- Voice — does it sound like Dan, or like a generic technical post?
- Story — did the Content agent find the actual narrative in the commits, or just summarize them?
- SEO — are the title, meta, and tags reasonable?
- Length — too short, too long, just right?

**If voice is off:** the Content agent backstory in `agents/content_agent.py:CONTENT_SYSTEM_PROMPT` is the place to tune. Iterate, redraft the same batch.

**If happy:** proceed to step 9.

### 9. Run the full backlog crawl

Remove the single-batch cap. Run the full crawl. Expect 20–50 drafts to appear in Ghost.

```bash
python -m pipelines.blog_pipeline.runner
```

This may take 10–30 minutes depending on commit count and rate limits.

### 10. Wire the cron schedule

```bash
crontab -e
# Add:
0 */4 * * * /srv/ai-agent-platform/scripts/run_blog_pipeline.sh >> /var/log/blog_pipeline.log 2>&1
```

Check after the next quarter-hour boundary that a fresh `pipeline_runs` row appears.

---

## What's deferred (NOT for this SSH session)

- Drip publisher (throttled "approved → published" job at 2-3/week)
- Hashnode and Dev.to syndication
- Markdown-to-HTML rendering polish (current `_body_to_html` is a paragraph-only placeholder)
- Cron overlap protection via Postgres advisory lock
- Cohesion graph link-candidate ranking call (graph is populated, but `runner.py` passes empty `candidates`)
- Sysadmin agent
- Developer / Solution Engineer agents

These are Sprint One+ work.

---

## Troubleshooting

### Postgres connection refused
- Check `POSTGRES_PASSWORD` matches what Postgres was initialized with
- Check the container is running: `docker ps | grep hvac-postgres`

### Ghost JWT 401
- Admin API key format: `<24 hex chars>:<64 hex chars>` — separated by colon
- The secret half is hex, not base64. The publisher converts it via `bytes.fromhex`.
- Token TTL is 5 minutes. If clock is skewed on the VPS, regenerate.

### Anthropic 429
- Rate limited. Backlog crawls at high concurrency can trigger this. Re-run — the runner is idempotent (existing drafts are detected by slug).

### "module not found"
- Confirm `pip install -e .` ran from the repo root
- If using the venv, make sure cron's wrapper script activates it (the current `run_blog_pipeline.sh` does NOT — add a `source .venv/bin/activate` line if needed)

### Triviality filter eats real commits
- The default filter is conservative on `chore:` `style:` `typo` `bump` `wip` and any commit ≤5 lines. If predictor_ingest's commit conventions are different, edit `TRIVIAL_SUBJECT_PATTERNS` in `commit_batcher.py`.

---

## State to capture back into the cloud session

When SSH work wraps up, note these for the next planning round:

- Number of backlog drafts generated
- Total tokens consumed (sum from `agent_decisions`)
- Director's voice-quality verdict on the first 5 drafts
- Any prompt tweaks made to `CONTENT_SYSTEM_PROMPT` or `MARKETER_SYSTEM_PROMPT`
- Triviality filter tuning (if any)
- Whether the cohesion graph's empty `candidates` list noticeably hurt link quality

These feed Sprint One planning: drip publisher, link-ranking integration, voice calibration loop.
