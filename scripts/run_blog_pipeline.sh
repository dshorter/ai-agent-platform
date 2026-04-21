#!/usr/bin/env bash
# Cron entry point for the commit-to-blog pipeline.
#
# Usage: crontab entry like
#   0 */4 * * * /srv/ai-agent-platform/scripts/run_blog_pipeline.sh
#
# Expects an adjacent .env file (not committed) providing:
#   ANTHROPIC_API_KEY
#   GHOST_ADMIN_API_KEY
#   POSTGRES_DSN
#   PIPELINE_SOURCE_REPO
#   PIPELINE_SOURCE_NAME
#   PIPELINE_PROJECT_CONTEXT
#   GHOST_ADMIN_URL

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ -f "$REPO_ROOT/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$REPO_ROOT/.env"
    set +a
fi

# Postgres advisory lock prevents cron overlap. 7913 is an arbitrary namespace.
exec python -m pipelines.blog_pipeline.runner "$@"
