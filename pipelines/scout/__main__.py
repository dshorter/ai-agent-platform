"""Scout entrypoints.

    python -m pipelines.scout --ingest             # session JSONL -> scout_session_log (run as root)
    python -m pipelines.scout --pass               # walk + synthesize + file leads
    python -m pipelines.scout --pass --dry-run     # rehearse: print leads, consume no coverage
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys

import psycopg

from pipelines.scout.config import ScoutConfig


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # Operator pause switch: SCOUT_PAUSED=1 in .env idles the whole pass
    # (ingest included — the cursor catches ingest up on resume). Exit 0 so
    # the timer's OnFailure page stays quiet; this is a pause, not a failure.
    if os.environ.get("SCOUT_PAUSED"):
        print("scout: paused (SCOUT_PAUSED set in .env) — remove the line to resume")
        return
    parser = argparse.ArgumentParser(prog="scout")
    parser.add_argument("--ingest", action="store_true", help="ingest session logs into Postgres")
    parser.add_argument("--pass", dest="do_pass", action="store_true", help="run one prospecting pass")
    parser.add_argument("--dry-run", action="store_true", help="with --pass: print leads, persist nothing")
    args = parser.parse_args()

    config = ScoutConfig.from_env()
    if not (args.ingest or args.do_pass):
        parser.print_help()
        sys.exit(1)

    if args.ingest:
        from pipelines.scout.ingest import ingest

        conn = psycopg.connect(config.postgres_dsn)
        try:
            stats = ingest(conn, config.logs_dir, config.codex_logs_dir)
        finally:
            conn.close()
        print(json.dumps(stats))

    if args.do_pass:
        if not config.anthropic_api_key:
            sys.exit("ANTHROPIC_API_KEY not set.")
        from pipelines.scout.run import run_pass

        summary = run_pass(config, dry_run=args.dry_run)
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
