# AI Agent Platform

> **A generic spine for running semi-autonomous AI crews against real projects.**

A code-first agent platform built on the Claude Agent SDK, Postgres, and Docker. Designed to host multiple pipelines (commit-to-blog, monitoring, scheduling) against multiple targets under one observability spine.

---

## Current tenants

| Pipeline | Status | Source | Target |
|----------|--------|--------|--------|
| **Uzelhub blog pipeline** | Sprint Zero scaffolding | `predictor_ingest` commit history | Ghost @ uzelhub.com |
| **HVAC digital twin** | Archived test case (first proof) | n8n workflows | Portfolio demo |

The HVAC work is preserved in-repo — schema, workflows, and portfolio pages are all still there if the demo needs to be resurrected. New development happens against the generic platform spine.

---

## Platform design

### Spine (all pipelines share)

- **Postgres database `ai_agent_platform`** — `pipeline_runs`, `pipeline_inputs`, `agent_decisions`, `posts`, `business_metrics`. Sequence-aware logging (LOG003 pattern) across every agent invocation.
- **Claude Agent SDK** — code-defined subagents, not visual workflows. Prompt caching on stable backstories.
- **Cron-driven runners** — plain Python scripts invoked on a schedule. No orchestrator service.
- **MCP tools where they fit** — GitHub MCP for remote repos, direct API calls for everything else.

### First pipeline: Uzelhub commit-to-blog

Crawls `predictor_ingest` commit history, clusters commits into story batches, drafts posts in Dan Uzel's voice via a Content agent, packages them with SEO via a Marketer agent, and POSTs to Ghost as drafts for Blog Director review.

Design details: [`docs/uzelhub-crew/sprint-zero-kickoff.md`](docs/uzelhub-crew/sprint-zero-kickoff.md).

Key modules:
- `agents/content_agent.py` — voice writer (Sonnet)
- `agents/marketer_agent.py` — SEO packaging (Sonnet + Haiku extraction)
- `pipelines/blog_pipeline/` — git reader, commit batcher, Ghost publisher, logging context, cohesion graph, runner
- `scripts/run_blog_pipeline.sh` — cron wrapper

---

## Tech stack

- **Orchestration** — Python + cron, Claude Agent SDK
- **Database** — PostgreSQL 15, two DBs on one instance (`ai_agent_platform` generic, `hvac_demo` archived)
- **Web** — Nginx serving static portfolio pages
- **Tunneling** — ngrok (for portfolio / demo access, not pipeline inputs)
- **LLM** — Claude Sonnet + Haiku via the Anthropic API
- **CMS target** — Ghost (running separately on the same VPS, not in this compose)

---

## Quick start

### Prerequisites

- Docker and Docker Compose
- An `ANTHROPIC_API_KEY`
- Ghost running somewhere reachable (for pipeline publishing) — optional for scaffolding
- Python 3.11+ if running agents outside Docker

### Bring up the stack

```bash
docker-compose up -d
```

This starts:
- **Postgres** on `127.0.0.1:5432` — creates both `hvac_demo` and `ai_agent_platform` databases on first boot
- **Nginx** on `127.0.0.1:8080` — portfolio pages
- **ngrok** — public tunnel to the portfolio

The `predictor` service runs under a Docker profile — bring it up explicitly when you need it:

```bash
docker-compose --profile predictor up -d predictor
```

### Run the blog pipeline (dry run)

```bash
pip install -e .
export PIPELINE_SOURCE_REPO=/path/to/predictor_ingest
export ANTHROPIC_API_KEY=sk-...
python -m pipelines.blog_pipeline.runner --dry-run
```

A dry run reads commits, filters triviality, groups into batches, and prints the result. No LLM calls, no DB writes, no Ghost POSTs.

### Production cron

```bash
# crontab -e
0 */4 * * * /srv/ai-agent-platform/scripts/run_blog_pipeline.sh
```

The wrapper script sources `.env` and invokes the Python runner.

---

## Repository layout

```
ai-agent-platform/
├── agents/                        # Subagent definitions (Content, Marketer)
├── pipelines/
│   └── blog_pipeline/             # Commit-to-blog pipeline modules
├── database/
│   ├── ai_agent_platform/         # Generic platform schema (active)
│   ├── hvac_schema.sql            # HVAC test-case schema (archived, still runnable)
│   ├── init/                      # Docker entrypoint init scripts
│   └── README.md                  # DB setup and migration notes
├── docs/
│   ├── uzelhub-crew/              # Sprint-zero decisions, design docs
│   ├── 00-hopper/ ... 05-development/   # HVAC-era docs (archived, some generic)
│   └── 05-development/code-examples/    # Sequence-aware-logging reference
├── n8n-workflows/                 # Archived HVAC test-case workflows (not running)
├── nginx/                         # Nginx config for the portfolio site
├── predictor/                     # Predictor pipeline Dockerfile (context is a sibling repo)
├── public/                        # Portfolio and dashboard HTML
├── scripts/                       # Operations and cron wrappers
├── docker-compose.yml             # Postgres + nginx + ngrok + (profile) predictor
└── pyproject.toml                 # Python package for the agent pipelines
```

---

## Documentation

- **Platform kickoff and design** — [`docs/uzelhub-crew/sprint-zero-kickoff.md`](docs/uzelhub-crew/sprint-zero-kickoff.md)
- **Database setup and migration** — [`database/README.md`](database/README.md)
- **HVAC test-case docs (archived reference)** — [`docs/`](docs/) (folders `00-hopper` through `05-development`)

---

## Status

**Active development** — Sprint Zero scaffolding landed, integration against the VPS and first real run next.

**Platform invariants that survived the n8n → code-first transition:**
- Sequence-aware logging schema — unchanged, proven generic
- Predictor pipeline integration — unchanged, remains a key data source for future Sysadmin agent ([design draft](docs/uzelhub-crew/sysadmin-agent-design.md))
- Portfolio site — unchanged, still served by nginx
- Docker Compose chassis — Postgres and nginx kept, n8n retired

---

## License

MIT — see [LICENSE](LICENSE).

---

## Maintainer

**Daniel Shorter** · codesurfer@gmail.com · [@dshorter](https://github.com/dshorter)
