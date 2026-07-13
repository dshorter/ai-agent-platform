#!/bin/bash
# Deploy: sync the tree, then reconcile containers — WITHOUT tearing the
# stack down. The old version ran `docker compose down` + `pull` + `up -d`
# on every push to main, which bounced hvac-postgres/ngrok per push and
# silently killed every long-lived DB connection on the box (found
# 2026-07-13: the Director listener's "disconnect error"). `up -d` alone
# recreates only services whose config actually changed, so a docs-only
# push is a docker no-op.
set -euo pipefail

echo "Deploying AI Agent Platform... $(date)"

cd /opt/ai-agent-platform || exit 1

# The tree is owned by claude; the workflow SSHes in as root. Pull as the
# owner so git's dubious-ownership guard doesn't reject it.
echo "Pulling latest changes..."
sudo -u claude git pull --ff-only origin main

# Reconcile the live services by name (the _host README rule: never bare
# `up -d` where compose files overlap). --no-deps because ngrok declares
# depends_on: web — the dead nginx that loses the port-80 fight with caddy
# every time (its removal is an open operator TODO on the ops calendar);
# `predictor` stays profile-gated. Recreates only config-drifted services.
echo "Reconciling containers..."
docker compose up -d --no-deps postgres ngrok

echo "Current status:"
docker compose ps

echo "Deployment complete."
