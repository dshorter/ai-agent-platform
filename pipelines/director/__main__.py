"""Run the Director.

    python -m pipelines.director                      # start the Telegram listener
    python -m pipelines.director --selftest "msg"      # one reasoning turn, no Telegram
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

    from pipelines.director.listener import run_listener

    run_listener(config)


if __name__ == "__main__":
    main()
