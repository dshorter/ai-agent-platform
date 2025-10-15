#!/usr/bin/env bash
# AI Agent Platform Health Check Script
# Last updated: 2025-10-14
set -euo pipefail

PROJECT_DIR="/opt/ai-agent-platform"
LOG_FILE="/var/log/agent-platform-health.log"
ALERT_EMAIL="${ALERT_EMAIL:-}"  # Set via environment or systemd unit
MAX_RESTART_ATTEMPTS=3

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
    logger -t agent-platform-health "$*"
}

alert() {
    local msg="$1"
    log "ALERT: $msg"
    
    # Send email if configured
    if [[ -n "$ALERT_EMAIL" ]] && command -v mail >/dev/null 2>&1; then
        echo "$msg" | mail -s "Agent Platform Alert" "$ALERT_EMAIL"
    fi
    
    # Could also send to Slack, PagerDuty, etc. here
}

check_docker_running() {
    if ! docker info >/dev/null 2>&1; then
        alert "Docker daemon is not running!"
        return 1
    fi
    return 0
}

ensure_stack_running() {
    log "Ensuring Docker Compose stack is running..."
    
    cd "$PROJECT_DIR" || {
        alert "Cannot access project directory: $PROJECT_DIR"
        return 1
    }
    
    $COMPOSE up -d || {
        alert "Failed to start Docker Compose stack"
        return 1
    }
    
    log "✓ Docker Compose stack is up"
}

check_container_status() {
    local container="$1"
    
    if ! docker ps --filter "name=$container" --filter "status=running" | grep -q "$container"; then
        log "WARNING: Container '$container' is not running"
        return 1
    fi
    
    # Check if container is healthy (if health check is defined)
    local health
    health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "none")
    
    if [[ "$health" == "unhealthy" ]]; then
        log "WARNING: Container '$container' is unhealthy"
        return 1
    fi
    
    return 0
}

check_n8n_health() {
    log "Checking n8n health..."
    
    # Check container status
    if ! check_container_status "n8n"; then
        return 1
    fi
    
    # Check n8n API endpoint
    local retry_count=0
    local max_retries=3
    
    while [[ $retry_count -lt $max_retries ]]; do
        if curl -sf --max-time 5 http://localhost:5678/healthz >/dev/null 2>&1; then
            log "✓ n8n API is responding"
            return 0
        fi
        
        log "n8n API check failed (attempt $((retry_count + 1))/$max_retries)"
        retry_count=$((retry_count + 1))
        sleep 2
    done
    
    alert "n8n API is not responding after $max_retries attempts"
    return 1
}

check_ngrok_health() {
    log "Checking ngrok health..."
    
    # Check container status
    if ! check_container_status "ngrok"; then
        return 1
    fi
    
    # Check ngrok API
    if curl -sf --max-time 5 http://localhost:4040/api/tunnels >/dev/null 2>&1; then
        # Get tunnel URL
        local tunnel_url
        tunnel_url=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url' 2>/dev/null || echo "unknown")
        log "✓ ngrok is running - Tunnel: $tunnel_url"
        return 0
    else
        log "WARNING: ngrok API is not responding"
        return 1
    fi
}

check_disk_space() {
    log "Checking disk space..."
    
    local usage
    usage=$(df -h "$PROJECT_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [[ $usage -gt 90 ]]; then
        alert "Disk space critical: ${usage}% used"
        return 1
    elif [[ $usage -gt 80 ]]; then
        log "WARNING: Disk space at ${usage}%"
    else
        log "✓ Disk space OK: ${usage}% used"
    fi
    
    return 0
}

check_recent_errors() {
    log "Checking recent errors in n8n logs..."
    
    local error_count
    error_count=$(docker logs --since=5m n8n 2>&1 | grep -ciE "error|exception|failed" || echo "0")
    
    if [[ $error_count -gt 10 ]]; then
        alert "High error rate in n8n: $error_count errors in last 5 minutes"
        
        # Show sample errors
        log "Recent errors:"
        docker logs --since=5m n8n 2>&1 | grep -iE "error|exception" | tail -5 | tee -a "$LOG_FILE"
        
        return 1
    elif [[ $error_count -gt 0 ]]; then
        log "Found $error_count error(s) in last 5 minutes (within acceptable range)"
    fi
    
    return 0
}

show_status() {
    log "Current system status:"
    
    echo "════════════════════════════════════════════════════════" | tee -a "$LOG_FILE"
    $COMPOSE -f "$PROJECT_DIR/docker-compose.yml" ps | tee -a "$LOG_FILE"
    echo "════════════════════════════════════════════════════════" | tee -a "$LOG_FILE"
}

attempt_recovery() {
    local component="$1"
    
    log "Attempting to recover $component..."
    
    case "$component" in
        n8n|ngrok)
            log "Restarting $component container..."
            docker restart "$component" || {
                alert "Failed to restart $component"
                return 1
            }
            
            sleep 10  # Give it time to start
            
            if [[ "$component" == "n8n" ]]; then
                check_n8n_health
            else
                check_ngrok_health
            fi
            ;;
        *)
            log "Unknown component for recovery: $component"
            return 1
            ;;
    esac
}

run_health_checks() {
    local failed_checks=()
    
    log "════════════════════════════════════════════════════════"
    log "Starting health checks..."
    log "════════════════════════════════════════════════════════"
    
    # Docker daemon check
    check_docker_running || failed_checks+=("docker")
    
    # Ensure stack is up
    ensure_stack_running || failed_checks+=("stack")
    
    # Component health checks
    check_n8n_health || failed_checks+=("n8n")
    check_ngrok_health || failed_checks+=("ngrok")
    
    # System checks
    check_disk_space || failed_checks+=("disk")
    check_recent_errors || failed_checks+=("errors")
    
    # Show current status
    show_status
    
    # Report results
    if [[ ${#failed_checks[@]} -eq 0 ]]; then
        log "════════════════════════════════════════════════════════"
        log "✓ All health checks passed"
        log "════════════════════════════════════════════════════════"
        return 0
    else
        log "════════════════════════════════════════════════════════"
        log "⚠ Health check failures: ${failed_checks[*]}"
        log "════════════════════════════════════════════════════════"
        
        # Attempt recovery for critical components
        for component in "${failed_checks[@]}"; do
            case "$component" in
                n8n|ngrok)
                    attempt_recovery "$component"
                    ;;
            esac
        done
        
        return 1
    fi
}

### MAIN ###
main() {
    # Rotate log if it gets too big (keep last 10MB)
    if [[ -f "$LOG_FILE" ]] && [[ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null) -gt 10485760 ]]; then
        mv "$LOG_FILE" "$LOG_FILE.old"
    fi
    
    run_health_checks
    exit $?
}

main "$@"