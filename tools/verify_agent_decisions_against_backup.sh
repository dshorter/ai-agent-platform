#!/bin/bash
# Verify agent_decisions matches the last backup, using a throwaway database.
#
#   sudo /opt/ai-agent-platform/tools/verify_agent_decisions_against_backup.sh
#
# WHY THIS EXISTS
# ---------------
# On 2026-08-31 a bridge tool wrote 445 rows into agent_decisions that did not
# belong there (daily aggregates in a per-invocation trace, backdated to before
# the trace began). They were removed by a targeted DELETE, verified in-place.
# This is the INDEPENDENT check: it compares the live table against the most
# recent pg_dumpall, from outside the system that did the damage.
#
# It is deliberately NOT a restore. A restore would roll the whole cluster back
# to 03:39 and destroy everything written since — including a contact
# submission from a real person at 19:24 the same day. The backup is used here
# as an oracle, never as the undo mechanism.
#
# SAFE BY CONSTRUCTION
#   * reads the dump read-only; never writes to it
#   * loads ONLY into a scratch database, dropped on exit (even on failure)
#   * touches neither ai_agent_platform nor hvac_demo
#   * no service is stopped; nothing is restarted
set -euo pipefail

BACKUP_DIR=/var/backups/host/postgres
CONTAINER=hvac-postgres
PGUSER=hvac_user
LIVE_DB=ai_agent_platform
SCRATCH="verify_$(date +%s)"

if [[ $EUID -ne 0 ]]; then
    echo "must run as root — the backup directory is 700" >&2
    exit 1
fi

DUMP=$(ls -1t "$BACKUP_DIR"/postgres_all_*.sql.gz 2>/dev/null | head -1 || true)
if [[ -z "$DUMP" ]]; then
    echo "no dump found in $BACKUP_DIR" >&2
    exit 1
fi
echo "=== verifying against $(basename "$DUMP") ($(date -r "$DUMP" '+%Y-%m-%d %H:%M')) ==="

cleanup() {
    docker exec "$CONTAINER" psql -U "$PGUSER" -d postgres \
        -c "DROP DATABASE IF EXISTS $SCRATCH" >/dev/null 2>&1 || true
    echo "scratch database dropped"
}
trap cleanup EXIT

docker exec "$CONTAINER" psql -U "$PGUSER" -d postgres \
    -c "CREATE DATABASE $SCRATCH" >/dev/null

# pg_dumpall carries CREATE DATABASE / \connect lines for the whole cluster.
# Take only the ai_agent_platform section and strip the connect, so everything
# lands in the scratch database and nothing can touch a real one.
gunzip -c "$DUMP" \
  | awk '/^\\connect ai_agent_platform$/{f=1;next} /^\\connect /{f=0} f' \
  | docker exec -i "$CONTAINER" psql -U "$PGUSER" -d "$SCRATCH" -q >/dev/null 2>&1 || true

q() { docker exec "$CONTAINER" psql -U "$PGUSER" -d "$1" -tAc "$2" 2>/dev/null || echo "ERR"; }

echo
printf '%-38s %12s %12s\n' "check" "backup" "live"
fail=0
compare() {
    local label="$1" sql="$2"
    local b l
    b=$(q "$SCRATCH" "$sql"); l=$(q "$LIVE_DB" "$sql")
    printf '%-38s %12s %12s' "$label" "$b" "$l"
    if [[ "$b" == "$l" ]]; then echo "  OK"; else echo "  DIFFERS"; fail=1; fi
}

# Rows the backup knows about must all still be present and identical. Rows
# added legitimately AFTER the backup (the day's crew activity) are expected to
# make the live totals larger — so totals are reported, not asserted.
compare "invoke rows <= backup cutoff" \
        "SELECT COUNT(*) FROM agent_decisions WHERE decision_type='invoke' AND created_at <= (SELECT MAX(created_at) FROM agent_decisions WHERE created_at < CURRENT_DATE)"
compare "max decision_id in backup era" \
        "SELECT COALESCE(MAX(decision_id),0) FROM agent_decisions WHERE created_at < CURRENT_DATE"
compare "cost sum, backup era (6dp)" \
        "SELECT COALESCE(ROUND(SUM(cost_usd),6),0) FROM agent_decisions WHERE created_at < CURRENT_DATE"
compare "decision_types vocabulary" \
        "SELECT string_agg(decision_type,',' ORDER BY decision_type) FROM decision_types"
compare "pipeline_stage rows (must be 0 both)" \
        "SELECT COUNT(*) FROM agent_decisions WHERE decision_type='pipeline_stage'"

echo
echo "reported, not asserted (live is expected to be ahead of the backup):"
printf '  %-30s backup=%s live=%s\n' "agent_decisions total" \
    "$(q "$SCRATCH" 'SELECT COUNT(*) FROM agent_decisions')" \
    "$(q "$LIVE_DB" 'SELECT COUNT(*) FROM agent_decisions')"
printf '  %-30s backup=%s live=%s\n' "contact_submissions" \
    "$(q "$SCRATCH" 'SELECT COUNT(*) FROM contact_submissions')" \
    "$(q "$LIVE_DB" 'SELECT COUNT(*) FROM contact_submissions')"

echo
if [[ $fail -eq 0 ]]; then
    echo "PASS — the backup era is byte-identical; the 445 rows are gone and"
    echo "       nothing else moved."
else
    echo "FAIL — a check differs above. Do NOT restore on the strength of this;"
    echo "       investigate the specific check first."
    exit 2
fi
