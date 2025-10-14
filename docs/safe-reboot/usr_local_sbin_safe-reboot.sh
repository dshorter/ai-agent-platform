#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/opt/ai-agent-platform"
DATA_DIR="/root/n8n-data"
COMPOSE="docker compose"           # or: docker-compose if older systems
BACKUP_SCRIPT="$PROJECT_DIR/scripts/backup.sh"

log() { printf "[%s] %s\n" "$(date +'%F %T')" "$*"; }

require_root() {
  if [[ $EUID -ne 0 ]]; then
    echo "Please run as root (use sudo)"; exit 1
  fi
}

check_tools() {
  for t in docker ${COMPOSE%% *}; do
    command -v "$t" >/dev/null 2>&1 || { echo "Missing: $t"; exit 1; }
  done
}

preflight() {
  require_root
  check_tools
  [[ -d "$PROJECT_DIR" ]] || { echo "Missing $PROJECT_DIR"; exit 1; }
  [[ -d "$DATA_DIR" ]] || { echo "Missing $DATA_DIR"; exit 1; }
}

graceful_stop() {
  log "Exporting quick status..."
  $COMPOSE -f "$PROJECT_DIR/docker-compose.yml" ps || true

  log "Draining n8n active executions (best-effort)..."
  # If n8n queue is enabled, you could pause it here via API.
  # Otherwise give running jobs a short grace period:
  sleep 5

  log "Running backup script (workflows, DB, transactions)..."
  if [[ -x "$BACKUP_SCRIPT" ]]; then
    "$BACKUP_SCRIPT" || { echo "Backup script failed"; exit 1; }
  else
    echo "Backup script not executable or missing: $BACKUP_SCRIPT"
  fi

  log "Stopping containers (n8n, ngrok)..."
  (cd "$PROJECT_DIR" && $COMPOSE down)
}

sync_disks() {
  log "Syncing filesystems..."
  sync
}

reboot_now() {
  log "Rebooting system..."
  systemctl reboot || shutdown -r now
}

### main
preflight
graceful_stop
sync_disks
reboot_now
