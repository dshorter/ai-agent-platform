# Uzelhub Crew — Sprint Zero Kickoff

> **Status:** Scaffolding  
> **Branch:** `claude/uzelhub-crew-sprint-zero`  
> **Scope:** Commit-to-blog pipeline for `predictor_ingest` → Ghost (uzelhub.com)

---

## What this is

The first working pipeline of the Uzelhub AI Crew: a scripted crawler that reads the commit history of the `predictor_ingest` project, composes blog posts in Dan's voice, and publishes them as drafts to Ghost.

The broader crew architecture (Developer, Solution Engineer, Systems Admin agents) is deferred until after this pipeline proves itself.

---

## Decisions made

### Repository and framework

- **Home:** this repo (`ai-agent-platform`). It already has the sequence-aware logging schema, a Postgres-on-Hetzner chassis, and the predictor co-located.
- **Framework:** Claude Agent SDK (Python). Code-first agents, no visual workflow builder.
- **Orchestration:** plain cron on the Hetzner VPS calling a Python runner. No n8n.
- **HVAC artifacts:** archived under `archive/hvac/` in a subsequent PR. The n8n container is already not running.

### Pipeline shape

- **Source:** local `git log` against a `predictor_ingest` clone on the VPS. No GitHub API, no rate limits.
- **Target:** Ghost at `http://localhost:2368` via the Admin API (JWT-authenticated) on the same VPS.
- **Review queue:** Ghost's own drafts view. The Director approves, edits, or redirects inside Ghost admin. No custom Streamlit UI for v1.
- **Syndication:** Ghost canonical only. Hashnode and Dev.to deferred.

### Two-agent crew for v1

- **Content Agent** — writes in Dan's voice. Sonnet. Owns the prose.
- **Marketer Agent** — SEO packaging, titles, tags, meta, internal links. Mostly Sonnet with Haiku sub-calls for extractive work (keywords, tags, schema fields).

Developer, Solution Engineer, and Systems Admin agents are not built in this sprint.

### Model routing

At this volume (2-3 posts/week plus a one-time backlog crawl) cost is single-digit dollars either way. Model split is about fit and latency, not savings.

| Task | Model |
|------|-------|
| Full article composition | Sonnet |
| Title selection | Sonnet |
| Keyword/tag/schema extraction | Haiku |
| Topic clustering | Haiku |
| Post-descriptor extraction (for graph) | Haiku |
| Internal link candidate ranking | SQL + Haiku |
| Final link selection | Sonnet |
| Triviality filter | code + Haiku fallback |

### Backlog-first drafting

The first run crawls the full `predictor_ingest` history and produces all draft posts before any publish. This lets the Marketer's link pass see the entire corpus, not just "posts already on Ghost." Publishing is throttled separately — 2-3 per week — regardless of how many drafts exist.

### Lightweight JSON graph for cohesion

Each post emits a JSON descriptor at generation time (`topics`, `concepts`, `systems_mentioned`, `decisions_made`, `references`). Stored as JSONB on the post row. Internal-link candidates come from SQL queries over this graph, not from LLM similarity guesses. Smarter links, negligible cost.

### Idempotency

Scripted crawlers deduplicate themselves by tracking `MAX(commit_range_end)` per source repo. Two real idempotency concerns remain:

1. **Cron overlap** — Postgres advisory lock around each run.
2. **Ghost publish** — check for existing draft by slug before POST; store `ghost_post_id` immediately on success.

### Schema reuse

The existing `agent_decisions` table is generic under the HVAC names. It gets kept and extended. `workflow_executions` becomes `pipeline_runs`. `hvac_events` becomes `pipeline_inputs`. `customers`, `technicians`, and HVAC seed data go. Details in the PR 2 migration.

### Logging

The Python reference at `docs/05-development/code-examples/sequence-aware-logging.py` is adapted — not imported — into `pipelines/blog_pipeline/logging_context.py`. Extended with `llm_model`, `token_count_input/output`, `cost_usd`, and `decision_confidence` fields that match the `agent_decisions` schema columns.

---

## What Sprint Zero delivers

### PR 1 — scaffolding (this branch)

- Kickoff doc (this file)
- `agents/` package with Content and Marketer subagent definitions (working enough to call)
- `pipelines/blog_pipeline/` package: git reader, commit batcher, Ghost publisher, logging context, graph helpers, runner
- `scripts/run_blog_pipeline.sh` cron wrapper
- `pyproject.toml` declaring the Agent SDK and supporting deps

### PR 2 — cleanup (separate branch)

- Move HVAC artifacts under `archive/hvac/`
- `database/migrations/002_uzelhub_crew.sql`
- Strip n8n service from `docker-compose.yml`
- README rewrite

### Not in Sprint Zero

- Running the pipeline against real data (requires VPS)
- Schema migration application (happens on the VPS)
- Voice calibration (requires draft output to react to)
- Developer, Solution Engineer, Systems Admin agents
- Hashnode / Dev.to syndication
- Custom Director UI
- Sysadmin agent's weekly reflection loop

---

## Open knobs

These resolve by writing code and reacting to output, not by more planning.

- **Commit-batching heuristic** — default: group consecutive commits within a 48-hour window on overlapping file sets. Tune on real output.
- **Triviality filter** — default: regex against commit message prefixes (`chore:`, `typo`, `bump`, etc.) plus a minimum diff-size threshold. Haiku fallback for ambiguous cases.
- **Cron cadence** — every 4 hours (`0 */4 * * *`). One job runs the full pipeline: read new commits, draft what's batched, package, POST drafts to Ghost. Drip publisher runs as a separate job once that's built (Sprint One+).
- **Voice calibration loop** — TBD after the first 5 drafts.

---

## Deferred architectural questions

- Director UI (artifact vs Streamlit) — revisit after first month of use
- LinkedIn Articles as fourth syndication target
- CPX11 → CPX21 rescale — defer to actual memory pressure
- Prompt caching wiring — add when backstories stabilize
