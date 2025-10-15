#!/usr/bin/env bash
# AI Agent Platform Safe Reboot Script
# Last updated: 2025-10-14
set -euo pipefail

PROJECT_DIR="/opt/ai-agent-platform"
DATA_DIR="/root/n8n-data"
BACKUP_SCRIPT="$PROJECT_DIR/scripts/backup.sh"
LOG_FILE="/var/log/safe-reboot.log"
MAX_WAIT_SECONDS=300  # 5 minutes max wait for active executions

# Detect docker compose command
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE="docker-compose"
else
    echo "ERROR: Neither 'docker compose' nor 'docker-compose' found"
    exit 1
fi

log() { 
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg" | tee -a "$LOG_FILE"
    logger -t safe-reboot "$*"
}

error() {
    log "ERROR: $*"
    exit 1
}

require_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
    fi
}

check_tools() {
    local missing=()
    for tool in docker jq curl; do
        command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        error "Missing required tools: ${missing[*]}"
    fi
}

preflight() {
    log "Running preflight checks..."
    
    require_root
    check_tools
    
    [[ -d "$PROJECT_DIR" ]] || error "Project directory missing: $PROJECT_DIR"
    [[ -d "$DATA_DIR" ]] || error "Data directory missing: $DATA_DIR"
    [[ -x "$BACKUP_SCRIPT" ]] || error "Backup script missing or not executable: $BACKUP_SCRIPT"
    
    log "✓ Preflight checks passed"
}

check_n8n_health() {
    log "Checking n8n health..."
    
    if docker ps --filter "name=n8n" --filter "status=running" | grep -q n8n; then
        if curl -sf http://localhost:5678/healthz >/dev/null 2>&1; then
            log "✓ n8n is healthy"
            return 0
        else
            log "WARNING: n8n container running but health check failed"
            return 1
        fi
    else
        log "WARNING: n8n container not running"
        return 1
    fi
}

wait_for_executions() {
    log "Checking for active n8n executions..."
    
    local elapsed=0
    local active_count
    
    while [[ $elapsed -lt $MAX_WAIT_SECONDS ]]; do
        # Try to get active execution count via API or docker exec
        if active_count=$(docker exec n8n n8n execute:list --status=running --json 2>/dev/null | jq '. | length' 2>/dev/null); then
            if [[ "$active_count" -eq 0 ]]; then
                log "✓ No active executions - safe to proceed"
                return 0
            fi
            log "Waiting for $active_count active execution(s)... ($elapsed/$MAX_WAIT_SECONDS seconds elapsed)"
        else
            log "WARNING: Could not check execution status, proceeding after grace period"
            sleep 10
            return 0
        fi
        
        sleep 10
        elapsed=$((elapsed + 10))
    done
    
    log "WARNING: Timeout waiting for executions. Proceeding anyway (some data loss may occur)"
    return 1
}

export_status() {
    log "Exporting current status..."
    
    $COMPOSE -f "$PROJECT_DIR/docker-compose.yml" ps | tee -a "$LOG_FILE" || true
    
    log "Container logs (last 50 lines):"
    docker logs --tail=50 n8n 2>&1 | tee -a "$LOG_FILE" || true
}

run_backup() {
    log "Running backup script..."
    
    if ! "$BACKUP_SCRIPT"; then
        error "Backup failed - ABORTING REBOOT to prevent data loss"
    fi
    
    log "✓ Backup completed successfully"
}

graceful_stop() {
    log "Beginning graceful shutdown..."
    
    export_status
    check_n8n_health || log "WARNING: n8n health check failed before shutdown"
    wait_for_executions
    run_backup
    
    log "Stopping all containers..."
    (cd "$PROJECT_DIR" && $COMPOSE down) || error "Failed to stop containers"
    
    log "✓ All containers stopped"
}

sync_disks() {
    log "Syncing filesystems..."
    sync
    sleep 2  # Give kernel time to flush
    log "✓ Filesystems synced"
}

reboot_now() {
    log "════════════════════════════════════════════════════════"
    log "INITIATING SYSTEM REBOOT"
    log "════════════════════════════════════════════════════════"
    
    # Try systemctl first, fallback to shutdown
    if command -v systemctl >/dev/null 2>&1; then
        systemctl reboot
    else
        shutdown -r now
    fi
}

# Signal handlers for clean interruption
trap 'log "Script interrupted - cleanup may be incomplete!"; exit 130' INT TERM

### MAIN ###
main() {
    log "════════════════════════════════════════════════════════"
    log "AI Agent Platform Safe Reboot - Starting"
    log "════════════════════════════════════════════════════════"
    
    preflight
    graceful_stop
    sync_disks
    reboot_now
}

main "$@"