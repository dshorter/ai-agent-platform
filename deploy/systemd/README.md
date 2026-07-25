# Systemd unit sources — ai-agent-platform

Source-of-record copies of this repo's installed units (the predictor pattern:
units live in `/etc/systemd/system/`, sources live here, keep them in sync when
editing live units). Until 2026-07-23 this repo's units existed **only** in
`/etc` — a rebuild would have lost them; new units land here first.

| Unit | Job | Status |
|---|---|---|
| `sysadmin-daily.{service,timer}` | daily reconciliation pass, 06:20 ET | written 2026-07-23, **not yet installed** |

Existing live units NOT yet mirrored here (recreate from `/etc` if adopting):
`director-listener.service`, `director-morning-brief.{service,timer}`,
`scout-pass.{service,timer}`.

## Install block — sysadmin agent (operator, needs sudo)

```sh
# 1. The proposals home (design §Operating loop) — claude-owned, agent-writable
sudo mkdir -p /var/lib/sysadmin-agent/proposals
sudo chown -R claude:claude /var/lib/sysadmin-agent

# 2. The units
sudo cp /opt/ai-agent-platform/deploy/systemd/sysadmin-daily.service \
        /opt/ai-agent-platform/deploy/systemd/sysadmin-daily.timer \
        /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sysadmin-daily.timer

# 3. Journal access (recommended) — without it the agent is journal-blind and
#    recurring-incident detection is dead (design §Pre-build sweep, Identity)
sudo usermod -aG systemd-journal claude
```

Verify: `systemctl list-timers sysadmin-daily.timer` shows the next 06:20 fire;
first report lands in `/var/lib/sysadmin-agent/proposals/<date>-daily.md`.

Still-open identity gates (same section of the design doc): `gh auth login`
as claude (GitHub run-history reads), a read-only B2 audit key under claude's
own config (credential audits + restore drills). Neither blocks the daily pass.

Manual runs (no install needed):

```sh
cd /opt/ai-agent-platform
.venv/bin/python -m pipelines.sysadmin --selftest         # no API, no cost
.venv/bin/python -m pipelines.sysadmin --pass daily --dry-run
```

Pause switch: `SYSADMIN_PAUSED=1` in `.env` idles the pass (exit 0, no page) —
the SCOUT_PAUSED pattern; use it instead of touching the timer.
