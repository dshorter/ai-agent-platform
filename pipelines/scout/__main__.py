"""Scout entrypoints.

    python -m pipelines.scout --ingest             # session JSONL -> scout_session_log
                                                  # (runs even when paused; needs root ONLY for the
                                                  #  codex staging dir under /root — session logs are
                                                  #  readable as claude and are captured either way)
    python -m pipelines.scout --pass               # walk + synthesize + file leads
    python -m pipelines.scout --pass --dry-run     # rehearse: print leads, consume no coverage

The walk and the leap also run alone (scout-retool.md §2) — the walk is the
cheap tier and the leap is the premium one, so welding them made re-mining the
corpus cost ~$200 instead of ~$1:

    python -m pipelines.scout --walk --from-seq 0 --pages 95   # mine only, persist jewels
    python -m pipelines.scout --synthesize --since 2026-06-01 --until 2026-06-30

`--walk` moves NEITHER cursor. It re-reads ore the forward position has already
covered, and writing that position would rewind the Scout.
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
    # Operator pause switch: SCOUT_PAUSED=1 in .env idles the PASS. Exit 0 so
    # the timer's OnFailure page stays quiet; this is a pause, not a failure.
    #
    # Ingest is NOT gated (changed 2026-08-22). It used to be, justified by
    # "the cursor catches ingest up on resume" — which is wrong on its own
    # terms: the cursor catches up on the ore, not on the disk, and the disk
    # deletes itself. 30 ingested sessions no longer exist as files at all,
    # spanning 2026-06-03..08-02. Ingest is the only step in the whole system
    # whose gap is UNRECOVERABLE, it costs nothing (file reads and INSERTs, no
    # model call), and it files no leads — so it has no business being stopped
    # by a switch whose purpose is to stop the lead queue growing.
    #
    # It gates the AMBIENT verbs only. --walk and --synthesize are operator
    # actions, deliberately typed one at a time, and the reason to pause is
    # usually that you want to work the corpus by hand — which is exactly what
    # they are for. Refusing them here would make the pause switch mean "no
    # scout work at all", which is not what it is for.
    paused = bool(os.environ.get("SCOUT_PAUSED"))

    parser = argparse.ArgumentParser(prog="scout")
    parser.add_argument("--ingest", action="store_true", help="ingest session logs into Postgres")
    parser.add_argument("--pass", dest="do_pass", action="store_true", help="run one prospecting pass")
    parser.add_argument("--walk", action="store_true",
                        help="mine an explicit range and persist jewels; no synthesis, no cursor move")
    parser.add_argument("--synthesize", action="store_true",
                        help="surface leads from jewels already stored")
    parser.add_argument("--dry-run", action="store_true", help="print, persist nothing")
    walk_group = parser.add_argument_group("--walk")
    walk_group.add_argument("--from-seq", type=int, default=0, help="first seq to mine (exclusive)")
    walk_group.add_argument("--pages", type=int, default=None, help="max pages to mine (default: to the end)")
    syn_group = parser.add_argument_group("--synthesize")
    syn_group.add_argument("--since", help="earliest session_date (YYYY-MM-DD)")
    syn_group.add_argument("--until", help="latest session_date (YYYY-MM-DD)")
    syn_group.add_argument("--kind", action="append", help="jewel kind; repeatable")
    syn_group.add_argument("--of-run", help="only jewels from this mining run_id")
    syn_group.add_argument("--limit", type=int, help="cap the selection")
    args = parser.parse_args()

    verbs = (args.ingest, args.do_pass, args.walk, args.synthesize)
    if not any(verbs):
        parser.print_help()
        sys.exit(1)

    if paused and args.do_pass:
        print("scout: paused (SCOUT_PAUSED set in .env) — remove the line to resume")
        print("       --ingest still runs: capture is unrecoverable if a session")
        print("       log rotates away. --walk and --synthesize are operator verbs.")
        if not args.ingest:
            return
        args.do_pass = False

    config = ScoutConfig.from_env()

    if args.ingest:
        from pipelines.scout.ingest import ingest

        conn = psycopg.connect(config.postgres_dsn)
        try:
            stats = ingest(conn, config.logs_dir, config.codex_logs_dir)
        finally:
            conn.close()
        print(json.dumps(stats))

    if args.do_pass or args.walk or args.synthesize:
        if not config.anthropic_api_key:
            sys.exit("ANTHROPIC_API_KEY not set.")

    if args.do_pass:
        from pipelines.scout.run import run_pass

        print(json.dumps(run_pass(config, dry_run=args.dry_run), indent=2))

    if args.walk:
        from pipelines.scout.run import run_walk

        print(json.dumps(
            run_walk(config, from_seq=args.from_seq, max_pages=args.pages,
                     dry_run=args.dry_run),
            indent=2,
        ))

    if args.synthesize:
        from pipelines.scout.run import run_synthesis

        print(json.dumps(
            run_synthesis(config, since=args.since, until=args.until, kinds=args.kind,
                          of_run=args.of_run, limit=args.limit, dry_run=args.dry_run),
            indent=2,
        ))


if __name__ == "__main__":
    main()
