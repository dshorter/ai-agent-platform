"""Session-wide guards that a test cannot forget to apply.

The evidence-capture leak is on its third fix. The first (`a861925`) added
`state/empty-calls/`; tests promptly wrote residue into the live directory.
The second (`38aa9ba`) monkeypatched `__file__` in the tests that call
`_keep_evidence_if_empty` **directly** — and missed the two that reach it
through `_guard_truncation`, which calls it internally before raising. Two
files per test run kept landing in live state, unnoticed, until 2026-09-06.

That is the same shape as the bug the guard exists for: a fix applied to the
callers you can see, described as if it covered the path. So this one is not
a fix to two more tests. It redirects the directory for the whole session, so
a future test cannot reintroduce the leak by not knowing about it.
"""
import pytest


@pytest.fixture(autouse=True)
def _never_write_evidence_into_live_state(tmp_path, monkeypatch):
    import agents.scout_agent as scout

    root = tmp_path / "agents"
    root.mkdir(exist_ok=True)
    monkeypatch.setattr(scout, "__file__", str(root / "scout_agent.py"))
