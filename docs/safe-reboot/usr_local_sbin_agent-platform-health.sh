#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="/opt/ai-agent-platform"
COMPOSE="docker compose"

log() { printf "[%s] %s\n" "$(date +'%F %T')" "$*"; }

# Ensure stack is up
(cd "$PROJECT_DIR" && $COMPOSE up -d)

# Show status
$COMPOSE -f "$PROJECT_DIR/docker-compose.yml" ps

# Optional: tail logs briefly for errors
log "Recent n8n errors (last 2m), if any:"
docker logs --since=2m n8n 2>&1 | grep -iE "error|fail" || true
