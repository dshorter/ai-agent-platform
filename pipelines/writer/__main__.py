"""Writer entrypoints.

    python -m pipelines.writer --list                  # the desk's in-tray: claimed note leads
    python -m pipelines.writer --lead <id>             # draft it (requires status: claimed)
    python -m pipelines.writer --lead <id> --dry-run   # rehearse on any status; persist nothing
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

from pipelines.writer import assignment
from pipelines.writer.config import REGISTER_PROFILES, WriterConfig


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(prog="writer")
    parser.add_argument("--list", action="store_true", help="show claimed leads the v1 desk can draft")
    parser.add_argument("--lead", help="lead id to draft (from the leads ledger)")
    parser.add_argument("--dry-run", action="store_true", help="with --lead: print the note, persist nothing")
    args = parser.parse_args()

    config = WriterConfig.from_env()
    if not (args.list or args.lead):
        parser.print_help()
        sys.exit(1)

    if args.list:
        leads = assignment.load_leads(config.leads_path)
        claimed = [l for l in leads if l.get("status") == "claimed"]
        drafts = {p.stem for p in config.drafts_dir.glob("*.json")} if config.drafts_dir.is_dir() else set()
        if not claimed:
            print(
                f"in-tray empty: 0 of {len(leads)} leads are status: claimed — "
                "the Editor claims before the Writer drafts"
            )
        for lead in claimed:
            register = lead.get("register", "?")
            marker = "drafted" if lead["id"] in drafts else (
                "ready" if register in REGISTER_PROFILES else f"no {register} desk yet"
            )
            print(f"[{marker}] {lead['id']}  ({register})  {lead.get('pitch', '')[:90]}")

    if args.lead:
        if not config.anthropic_api_key:
            sys.exit("ANTHROPIC_API_KEY not set.")
        from pipelines.writer.run import run_draft

        summary = run_draft(config, args.lead, dry_run=args.dry_run)
        print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
