"""Run the sysadmin agent.

    python -m pipelines.sysadmin --pass daily            # one reconciliation pass
    python -m pipelines.sysadmin --pass daily --dry-run  # print only; no artifact, no ledger
    python -m pipelines.sysadmin --selftest              # structural checks, no API call
"""
from __future__ import annotations

import argparse
import logging


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(name)s %(message)s")
    ap = argparse.ArgumentParser(prog="pipelines.sysadmin")
    ap.add_argument("--pass", dest="pass_name", metavar="NAME",
                    help="run a reconciliation pass (daily)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the report; write no artifact, append no ledger entry")
    ap.add_argument("--selftest", action="store_true",
                    help="structural guard checks — no API call, no cost")
    args = ap.parse_args()

    if args.selftest:
        from pipelines.sysadmin.selftest import run_selftest

        raise SystemExit(run_selftest())

    if not args.pass_name:
        ap.error("nothing to do — use --pass daily or --selftest")

    from pipelines.sysadmin.config import SysadminConfig
    from pipelines.sysadmin.run import run_pass

    run_pass(SysadminConfig.from_env(), args.pass_name, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
