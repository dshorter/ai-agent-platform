#!/usr/bin/env bash
#
# Apply 006 — the leads ledger's tables and the pineapple grant.
#
#   ./apply-006-scout-lead.sh            # dump, apply, verify, tear out on failure
#   ./apply-006-scout-lead.sh --check    # preflight only: touches nothing
#   ./apply-006-scout-lead.sh --rollback # deliberate teardown
#
# Applying is additive: every object is new and nothing existing is altered, so
# this cannot change how the crew behaves today. Nothing reads these tables yet —
# leads.yaml is still the ledger until the store module lands.
#
# WHY THE DUMP IS NOT THE ROLLBACK. The cluster has no per-table restore point
# (AGENTS.md §Shared surfaces), so reloading a dump to undo a small mistake
# destroys everything written since it was taken. The rollback here is a precise
# DROP of exactly what 006 creates; the dump is the backstop for the case that
# cannot handle, and it is written OUTSIDE this repo because it contains
# transcript-derived rows and origin is public.
#
set -euo pipefail

CONTAINER="${PG_CONTAINER:-hvac-postgres}"
DB="${PG_DB:-ai_agent_platform}"
PG_USER="${PG_USER:-hvac_user}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="1.5.0"

psql_file() {  # <file>  — one file, stop on the first error
    docker exec -i "$CONTAINER" psql -v ON_ERROR_STOP=1 -U "$PG_USER" -d "$DB" < "$1"
}

psql_q() {     # <sql>   — one value, no decoration
    docker exec -i "$CONTAINER" psql -tAq -U "$PG_USER" -d "$DB" -c "$1"
}

say() { printf '%s\n' "$*"; }
die() { printf 'FAILED: %s\n' "$*" >&2; exit 1; }

# --- preflight --------------------------------------------------------------

say "== preflight"
command -v docker >/dev/null || die "docker is not on PATH"
docker ps --format '{{.Names}}' | grep -qx "$CONTAINER" \
    || die "container '$CONTAINER' is not running"
psql_q 'SELECT 1' >/dev/null || die "cannot reach $DB as $PG_USER"
say "   $CONTAINER up, $DB reachable as $PG_USER"

APPLIED="$(psql_q "SELECT count(*) FROM schema_version WHERE version_number = '$VERSION'")"
say "   schema_version $VERSION applied: $APPLIED"

if [[ "${1:-}" == "--rollback" ]]; then
    say "== rollback (deliberate)"
    psql_file "$HERE/006_rollback.sql"
    say "== done: 006 is out. scout_role is left in place, stripped of grants."
    exit 0
fi

if [[ "$APPLIED" != "0" ]]; then
    say "== nothing to do: $VERSION is already applied"
    say "   re-verify with:  docker exec -i $CONTAINER psql -v ON_ERROR_STOP=1 \\"
    say "                        -U $PG_USER -d $DB < $HERE/006_verify.sql"
    exit 0
fi

if [[ "${1:-}" == "--check" ]]; then
    say "== check only: preflight passed, $VERSION not applied, nothing written"
    exit 0
fi

# --- backup -----------------------------------------------------------------

say "== backup"
BACKUP_DIR="${DB_BACKUP_DIR:-/var/backups/ai-agent-platform}"
if ! mkdir -p "$BACKUP_DIR" 2>/dev/null; then
    BACKUP_DIR="$HOME/db-backups"
    mkdir -p "$BACKUP_DIR"
    say "   /var/backups not writable — using $BACKUP_DIR"
fi
case "$BACKUP_DIR" in
    "$HERE"*|"$(cd "$HERE/../.." && pwd)"*)
        die "refusing to dump inside the repo ($BACKUP_DIR): origin is public and \
this dump holds transcript-derived rows" ;;
esac

DUMP="$BACKUP_DIR/${DB}-pre-006-$(date +%Y%m%d-%H%M%S).sql"
docker exec "$CONTAINER" pg_dump -U "$PG_USER" -d "$DB" > "$DUMP"
chmod 600 "$DUMP"
# A dump that failed halfway is worse than no dump, because it looks like one.
grep -q 'PostgreSQL database dump complete' "$DUMP" \
    || die "the dump is truncated — nothing applied. See $DUMP"
say "   $DUMP ($(wc -c < "$DUMP") bytes, complete)"

# --- apply ------------------------------------------------------------------

say "== apply"
if ! psql_file "$HERE/006_scout_lead.sql"; then
    # 006 is one transaction: a failure here has already rolled itself back.
    die "006 did not apply; the transaction rolled back and nothing changed"
fi
say "   006 applied"

# --- self-verify ------------------------------------------------------------

say "== verify (in a transaction that is always rolled back)"
if ! psql_file "$HERE/006_verify.sql"; then
    say ""
    say "!! VERIFICATION FAILED — tearing 006 back out"
    psql_file "$HERE/006_rollback.sql" || \
        say "   the teardown ALSO failed. The dump is at $DUMP; read it before \
restoring, because a restore loses everything written since it was taken."
    die "006 verified badly and was removed"
fi

say "== done"
say "   schema_version: $(psql_q "SELECT version_number || ' — ' || applied_at \
FROM schema_version WHERE version_number = '$VERSION'")"
say "   grants:"
docker exec -i "$CONTAINER" psql -U "$PG_USER" -d "$DB" -c \
    "SELECT table_name, privilege_type, string_agg(column_name, ', ') AS columns
       FROM information_schema.column_privileges
      WHERE grantee = 'scout_role'
      GROUP BY table_name, privilege_type
      UNION ALL
     SELECT table_name, privilege_type, '(whole relation)'
       FROM information_schema.table_privileges
      WHERE grantee = 'scout_role'
      ORDER BY 1, 2"
say ""
say "   Nothing uses these tables yet: leads.yaml is still the ledger. The"
say "   cutover needs a store module, the 17 call sites moved, and the Scout"
say "   connecting as scout_role — a grant the process never connects under"
say "   enforces nothing."
say "   Undo:  $0 --rollback"
