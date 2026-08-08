"""Tests for the failed-pass ledger marker.

Why it exists: a failed pass writes no artifact and no ledger entry, so the day
it cost is invisible — and the next pass rhyme-checks against the *ledger*, so
a silent gap is exactly the gap it cannot find. That is how one failure class
took three days (2026-07-29, 08-04, 08-08) before anyone noticed it was one
class rather than three incidents.

The marker is a failure path, which means it is the code least likely to be
exercised and most likely to rot. These tests pin the three rules that make it
safe, in priority order:

  1. It must NEVER swallow the exception — the non-zero exit is what fires
     `OnFailure=notify-telegram@%n.service`. Swallowing turns a loud failure
     into a silent one and breaks a pager that has, verifiably, worked every
     time so far.
  2. A failure inside the marker must NEVER mask the original. A broken
     failure-handler that eats the real traceback is worse than none.
  3. It must not fire on a dry run, which writes nothing by contract.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipelines.sysadmin import run as run_mod  # noqa: E402


class _Boom(RuntimeError):
    """Stands in for whatever killed the pass — TruncatedRunError, a ValueError
    from the SDK guard, a timeout. The marker records the class, not the text."""


@pytest.fixture
def harness(monkeypatch):
    """Drive run_pass to the failure path with everything external stubbed."""
    calls: dict[str, list] = {"ledger": [], "notify": []}

    monkeypatch.setattr(run_mod, "PASSES", {"daily": "charter text"})
    monkeypatch.setattr(run_mod, "_gather_context", lambda *a, **k: "context")
    monkeypatch.setattr(run_mod, "_notify", lambda msg: calls["notify"].append(msg))
    monkeypatch.setattr(
        run_mod, "append_ledger",
        lambda config, title, body: calls["ledger"].append((title, body)) or "appended",
    )

    class _Agent:
        def __init__(self, *a, **k): ...
        def run(self, charter, context=None):
            raise _Boom("the pass died")

    monkeypatch.setattr(run_mod, "SysadminAgent", _Agent)
    monkeypatch.setattr(run_mod, "Anthropic", lambda **k: object())

    import psycopg
    monkeypatch.setattr(psycopg, "connect", lambda *a, **k: None)

    config = SimpleNamespace(
        paused=False, postgres_dsn="postgresql://x", anthropic_api_key="k",
        model="claude-sonnet-5", max_cost_usd=3.0,
        proposals_dir=Path("/tmp/does-not-matter"),
        ledger_path=Path("/tmp/does-not-matter/ledger.md"),
    )
    return config, calls


# --- rule 1: never swallow ------------------------------------------------


def test_the_original_exception_still_propagates(harness):
    """The non-zero exit is the pager. If this test ever fails, failures go
    silent and the OnFailure unit never runs."""
    config, _ = harness
    with pytest.raises(_Boom):
        run_mod.run_pass(config, "daily")


def test_marker_does_not_replace_the_exception_type(harness):
    """A caller (and systemd) must see the real cause, not a marker error."""
    config, _ = harness
    with pytest.raises(_Boom, match="the pass died"):
        run_mod.run_pass(config, "daily")


# --- rule 2: never mask ---------------------------------------------------


def test_a_broken_ledger_write_does_not_mask_the_real_failure(harness, monkeypatch):
    """The worst failure mode this code could have: the marker throws, and the
    operator gets a ledger error instead of the thing that actually broke."""
    config, _ = harness

    def _explode(*a, **k):
        raise OSError("ledger volume is read-only")

    monkeypatch.setattr(run_mod, "append_ledger", _explode)
    with pytest.raises(_Boom):          # _Boom, NOT OSError
        run_mod.run_pass(config, "daily")


# --- rule 3: content and dry-run ------------------------------------------


def test_marker_records_the_error_class_for_rhyme_checking(harness):
    """Three failures with three different literal errors were one class. The
    class is what a rhyme-check matches on, so it has to be in the title."""
    config, calls = harness
    with pytest.raises(_Boom):
        run_mod.run_pass(config, "daily")

    assert len(calls["ledger"]) == 1
    title, body = calls["ledger"][0]
    assert "FAILED" in title
    assert "_Boom" in title, "error class missing from the title"
    assert "no audit performed" in title
    assert "journalctl" in body, "no way to reach the detail"
    assert "rhyme-check" in body.lower(), "next pass isn't told to look for siblings"


def test_dry_run_writes_no_marker(harness):
    """A dry run writes nothing by contract — including on failure."""
    config, calls = harness
    with pytest.raises(_Boom):
        run_mod.run_pass(config, "daily", dry_run=True)
    assert calls["ledger"] == []


def test_a_paused_agent_is_not_a_failure(harness):
    """Pausing is an operator choice: exit 0, no marker, no pager."""
    config, calls = harness
    config.paused = True
    run_mod.run_pass(config, "daily")          # must not raise
    assert calls["ledger"] == []
