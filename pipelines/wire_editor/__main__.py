"""Wire Editor entrypoints.

    python -m pipelines.wire_editor --pass               # triage the new queue -> proposals artifact
    python -m pipelines.wire_editor --pass --dry-run     # same calls, print artifact, persist nothing
    python -m pipelines.wire_editor --concordance        # wire+chief vs operator verdicts (gate-1 metric)
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

from pipelines.wire_editor.config import WireEditorConfig
from pipelines.wire_editor.run import concordance, run_pass


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(prog="wire_editor")
    parser.add_argument("--pass", dest="do_pass", action="store_true", help="run one triage pass")
    parser.add_argument("--dry-run", action="store_true", help="with --pass: print artifact, persist nothing")
    parser.add_argument("--concordance", action="store_true", help="report suggestion-vs-verdict agreement")
    args = parser.parse_args()

    config = WireEditorConfig.from_env()
    if args.concordance:
        print(concordance(config))
        return
    if not args.do_pass:
        parser.print_help()
        sys.exit(1)
    if not config.anthropic_api_key:
        sys.exit("ANTHROPIC_API_KEY not set.")
    print(json.dumps(run_pass(config, dry_run=args.dry_run), indent=2))


if __name__ == "__main__":
    main()
