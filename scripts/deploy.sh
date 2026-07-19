#!/bin/bash
# Local container reconcile — run ON the box after compose-file changes.
# (Formerly the GitHub-Actions deploy leg; retired 2026-07-19. Box-native
# workflow: the tree here IS the source of truth, so pulling from origin
# was circular — the commit being "deployed" originated in this tree.)
#
# Reconciles WITHOUT tearing the stack down. The old version ran
# `docker compose down` + `pull` + `up -d` on every push to main, which
# bounced hvac-postgres/ngrok per push and silently killed every
# long-lived DB connection on the box (found 2026-07-13: the Director
# listener's "disconnect error"). `up -d` alone recreates only services
# whose config actually changed, so a docs-only change is a docker no-op.
set -euo pipefail

echo "Reconciling AI Agent Platform containers... $(date)"

cd /opt/ai-agent-platform || exit 1

# Reconcile the live services by name (the _host README rule: never bare
# `up -d` where compose files overlap). --no-deps because ngrok declares
# depends_on: web — the dead nginx that loses the port-80 fight with caddy
# every time (its removal is an open operator TODO on the ops calendar);
# `predictor` stays profile-gated. Recreates only config-drifted services.
docker compose up -d --no-deps postgres ngrok

echo "Current status:"
docker compose ps

echo "Reconcile complete."
