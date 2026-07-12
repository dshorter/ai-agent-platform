"""Run the Director.

    python -m pipelines.director                       # start the Telegram listener
    python -m pipelines.director --selftest "msg"       # one reasoning turn, no Telegram
    python -m pipelines.director --tick morning         # fire an ambient tick -> Telegram
    python -m pipelines.director --tick morning --dry-run  # ...but print instead of send
"""
from __future__ import annotations

import sys

from pipelines.director.config import DirectorConfig


def main() -> None:
    config = DirectorConfig.from_env()

    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        from pipelines.director.selftest import run_selftest

        message = (
            sys.argv[2]
            if len(sys.argv) > 2
            else "Across my projects, what should I work on first? Keep it brief."
        )
        run_selftest(config, message)
        return

    if len(sys.argv) > 1 and sys.argv[1] == "--tick":
        from pipelines.director.tick import run_tick

        name = (
            sys.argv[2]
            if len(sys.argv) > 2 and not sys.argv[2].startswith("-")
            else "morning"
        )
        run_tick(config, name, dry_run="--dry-run" in sys.argv)
        return

    from pipelines.director.listener import run_listener

    run_listener(config)


if __name__ == "__main__":
    main()
