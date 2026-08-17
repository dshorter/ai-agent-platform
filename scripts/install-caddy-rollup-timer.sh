#!/usr/bin/env bash
# Install the caddy-rollup timer. Run with sudo; safe to re-run.
#
#   sudo /opt/ai-agent-platform/scripts/install-caddy-rollup-timer.sh
#
# Runs at 06:00 — ahead of the sysadmin pass at 06:20, so the rollup for
# yesterday exists before the agent looks for it. Independent of the agent on
# purpose: a failed agent should not also mean no data.
#
# Pages on failure via OnFailure=notify-telegram@%n, matching backup.timer and
# agent-platform-health.timer. That matters here because the collector treats
# "parsed zero requests" as an error rather than a quiet day — a silent empty
# rollup would look exactly like a peaceful night.
set -euo pipefail

UNIT_DIR=/etc/systemd/system
REPO=/opt/ai-agent-platform
PY="$REPO/.venv/bin/python"
STAMP=$(date +%Y%m%d-%H%M%S)

[[ $EUID -eq 0 ]] || { echo "needs root: sudo $0" >&2; exit 1; }
[[ -x $PY ]] || { echo "missing venv at $PY" >&2; exit 1; }

# Verify the collector runs before installing anything that depends on it.
# stderr is NOT redirected: a hidden prompt or a swallowed traceback is how a
# script appears to hang with no cursor. Bounded, because the first run does
# uncached reverse-DNS lookups and a slow resolver should fail loudly rather
# than sit there. Output goes to a file so a clean run stays quiet.
echo "→ smoke test (dry run, writes nothing; up to 120s on a cold DNS cache)"
SMOKE=$(mktemp)
if ! timeout 120 runuser -u claude -- "$PY" -m tools.caddy_rollup --dry-run >"$SMOKE"; then
  echo "collector failed or timed out — not installing. Last output:" >&2
  tail -5 "$SMOKE" >&2
  rm -f "$SMOKE"; exit 1
fi
rm -f "$SMOKE"

for u in caddy-rollup.service caddy-rollup.timer; do
  [[ -f $UNIT_DIR/$u ]] && cp -a "$UNIT_DIR/$u" "$UNIT_DIR/.$u.backup.$STAMP"
done

cat > "$UNIT_DIR/caddy-rollup.service" <<UNIT
[Unit]
Description=Daily Caddy access-log rollup (visitors, verified crawlers, 404 classes)
Documentation=file://$REPO/tools/caddy_rollup.py
After=network-online.target
OnFailure=notify-telegram@%n.service

[Service]
Type=oneshot
User=claude
Group=claude
WorkingDirectory=$REPO
ExecStart=$PY -m tools.caddy_rollup
# Reads /var/log/caddy (world-readable) and writes only under the repo's
# gitignored state dir. Nothing else needs touching.
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$REPO/pipelines/sysadmin/state
ProtectHome=read-only
NoNewPrivileges=true
UNIT

cat > "$UNIT_DIR/caddy-rollup.timer" <<UNIT
[Unit]
Description=Run the Caddy rollup each morning before the sysadmin pass

[Timer]
OnCalendar=*-*-* 06:00:00 America/New_York
Persistent=true
RandomizedDelaySec=120

[Install]
WantedBy=timers.target
UNIT

systemd-analyze verify "$UNIT_DIR/caddy-rollup.service" "$UNIT_DIR/caddy-rollup.timer" \
  || { echo "unit files failed verification — restoring" >&2
       for u in caddy-rollup.service caddy-rollup.timer; do
         [[ -f $UNIT_DIR/.$u.backup.$STAMP ]] && mv "$UNIT_DIR/.$u.backup.$STAMP" "$UNIT_DIR/$u"
       done; exit 1; }

systemctl daemon-reload
systemctl enable --now caddy-rollup.timer

# One real run to prove the write path. Type=oneshot means `start` blocks until
# it finishes, so this is bounded too — and it reports rather than hangs.
echo "→ one real run, to prove the write path"
if ! timeout 180 systemctl start caddy-rollup.service; then
  echo "the service did not complete cleanly:" >&2
  journalctl -u caddy-rollup.service -n 20 --no-pager >&2
  exit 1
fi

echo
systemctl list-timers caddy-rollup.timer --no-pager
ls -la "$REPO/pipelines/sysadmin/state/caddy/" 2>/dev/null | tail -3
echo "installed. Backups of any prior units: $UNIT_DIR/.caddy-rollup.*.backup.$STAMP"
