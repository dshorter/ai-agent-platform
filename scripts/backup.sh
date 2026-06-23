#!/bin/bash

BACKUP_DIR="/root/n8n-data/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Starting backup at $TIMESTAMP"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# ── n8n ──────────────────────────────────────────────────────────────
# Backup n8n workflows
docker exec n8n n8n export:workflow --all --output=/data/backups/workflows_$TIMESTAMP.json

# Backup transaction data
if [ -d "/root/n8n-data/transactions" ]; then
    tar -czf $BACKUP_DIR/transactions_$TIMESTAMP.tar.gz -C /root/n8n-data transactions/
fi

# Backup n8n database
if [ -f "/root/n8n-data/database.sqlite" ]; then
    cp /root/n8n-data/database.sqlite $BACKUP_DIR/database_$TIMESTAMP.sqlite
fi

# ── Ghost (added 2026-05-10) ─────────────────────────────────────────
# DB: logical dump via mysqldump. Password comes from the container's own
# env, so we don't need to source /opt/server-maintenance/.env here.
if docker ps --filter "name=ghost-mysql" --filter "status=running" | grep -q ghost-mysql; then
    if docker exec ghost-mysql sh -c \
        'mysqldump --single-transaction --routines --triggers \
            -uroot -p"$MYSQL_ROOT_PASSWORD" ghost_prod' \
        > "$BACKUP_DIR/ghost_db_$TIMESTAMP.sql" 2>/dev/null; then
        gzip "$BACKUP_DIR/ghost_db_$TIMESTAMP.sql"
        echo "  ghost_db: ok"
    else
        rm -f "$BACKUP_DIR/ghost_db_$TIMESTAMP.sql"
        echo "  ghost_db: FAILED"
    fi
else
    echo "  ghost_db: skipped (container not running)"
fi

# Content volume (themes, uploads, members). Volume is project-prefixed.
if docker volume inspect server-maintenance_ghost-content >/dev/null 2>&1; then
    if docker run --rm \
        -v server-maintenance_ghost-content:/data:ro \
        -v "$BACKUP_DIR":/backup \
        alpine tar -czf "/backup/ghost_content_$TIMESTAMP.tar.gz" -C /data . 2>/dev/null; then
        echo "  ghost_content: ok"
    else
        rm -f "$BACKUP_DIR/ghost_content_$TIMESTAMP.tar.gz"
        echo "  ghost_content: FAILED"
    fi
else
    echo "  ghost_content: skipped (volume missing)"
fi

# ── Caddy (added 2026-05-10) ─────────────────────────────────────────
# Caddyfile is the routing source of truth; /var/lib/caddy has LE certs
# and ACME account state (re-issuable, but rate-limited).
if tar -czf "$BACKUP_DIR/caddy_$TIMESTAMP.tar.gz" \
        /etc/caddy/Caddyfile /var/lib/caddy 2>/dev/null; then
    echo "  caddy: ok"
else
    echo "  caddy: FAILED"
fi

# ── Retention ────────────────────────────────────────────────────────
# Keep only last 7 days of backups
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $TIMESTAMP"
ls -lh $BACKUP_DIR | tail -10
