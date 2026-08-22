"""The pass row budget — the knob the tuning actually turns.

Output is homeostatic at ~13 leads a pass no matter how much ore goes in, so
conversion runs 0.18 leads per jewel on a 450-row plate and ~1.0 on a small one
(docs/uzelhub-crew/scout-mining-economics.md). More ore per pass mines THINNER.
That makes "how many rows may one pass walk" the single number the retool
exists to correct, and an off-by-one-page bug here silently restores the old
behaviour while every test still passes.

So: exact arithmetic, no API, no database.
"""
from __future__ import annotations

import contextlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipelines.scout import run as run_mod  # noqa: E402
from pipelines.scout import walk as walk_mod  # noqa: E402
from pipelines.scout.config import ScoutConfig  # noqa: E402


class _Ctx:
    """Stands in for the spine's tool context — assigned to, never read."""

    def __setattr__(self, k, v):
        object.__setattr__(self, k, v)


class _LogManager:
    @contextlib.contextmanager
    def tool_sequence(self, *a, **k):
        yield _Ctx()


class _Call:
    model = "test-model"
    input_tokens = output_tokens = 0
    cache_creation_input_tokens = cache_read_input_tokens = 0

    def __init__(self):
        self.data = {"jewels": [], "scratchpad": [], "map_notes": []}


class _Agent:
    def triage(self, _prompt):
        return _Call()


@pytest.fixture
def harness(monkeypatch, tmp_path):
    """A walk with the ore, the model, and the writes all replaced — what is
    left under test is the paging arithmetic and nothing else."""
    served: list[int] = []

    def fake_fetch_page(_conn, after_seq, limit):
        served.append(limit)
        # An inexhaustible corpus, so any early stop is the budget's doing.
        return [
            {"seq": after_seq + i + 1, "date": "2026-06-01", "text": "x"}
            for i in range(limit)
        ]

    monkeypatch.setattr(walk_mod, "fetch_page", fake_fetch_page)
    monkeypatch.setattr(run_mod.walk, "page_as_prompt", lambda rows: "")
    monkeypatch.setattr(run_mod.jewels_mod, "persist", lambda *a, **k: 0)
    monkeypatch.setattr(run_mod.walk, "apply_scratchpad", lambda *a, **k: 0)
    monkeypatch.setattr(run_mod.walk, "append_map_notes", lambda *a, **k: None)
    saved: list[int] = []
    monkeypatch.setattr(run_mod.walk, "save_cursors", lambda _d, **kw: saved.append(kw))
    return served, saved


def _config(**over) -> ScoutConfig:
    base = dict(
        postgres_dsn="", anthropic_api_key="", walk_model="m", synthesis_model="m",
        synthesis_fallback="m", page_rows=150, pass_row_budget=150, roam_iterations=1,
        max_cost_usd=99.0, logs_dir=Path("/tmp"), codex_logs_dir=Path("/tmp"),
        state_dir=Path("/tmp"), leads_path=Path("/tmp/leads.yaml"),
    )
    base.update(over)
    return ScoutConfig(**base)


def _walk(config, budget, harness, cursor_key="forward", stop_at=None):
    summary = run_mod._blank_summary()
    found, cost, cursor = run_mod._walk_stage(
        conn=None, agent=_Agent(), config=config, log_manager=_LogManager(),
        run_id="r", cursor=0, row_budget=budget, summary=summary,
        dry_run=False, cursor_key=cursor_key, cost_cap=None, stop_at=stop_at,
    )
    return summary, cursor


def test_default_budget_is_one_page_not_three(harness):
    served, _ = harness
    summary, _ = _walk(_config(), 150, harness)
    assert served == [150]
    assert summary["rows"] == 150, "the 450-row plate is what we are moving away from"
    assert summary["pages"] == 1


def test_budget_is_a_row_count_not_a_page_count(harness):
    """A budget that is not a whole number of pages trims the last fetch
    instead of overshooting. A plate 149 rows over budget is still a bigger
    plate, and bigger plates are the entire problem."""
    served, _ = harness
    summary, _ = _walk(_config(), 250, harness)
    assert served == [150, 100]
    assert summary["rows"] == 250
    assert summary["pages"] == 2


def test_budget_smaller_than_a_page_is_honoured(harness):
    served, _ = harness
    summary, _ = _walk(_config(), 40, harness)
    assert served == [40]
    assert summary["rows"] == 40


def test_none_budget_is_unbounded_for_reclaim(harness, monkeypatch):
    """--walk passes None: the budget protects synthesis conversion and a
    reclaim sweep has no synthesis to protect. Bounded here only by the ore
    running out."""
    served: list[int] = []
    pages = {"left": 3}

    def finite_page(_conn, after_seq, limit):
        if not pages["left"]:
            return []
        pages["left"] -= 1
        served.append(limit)
        return [{"seq": after_seq + i + 1, "date": "2026-06-01", "text": "x"} for i in range(limit)]

    monkeypatch.setattr(walk_mod, "fetch_page", finite_page)
    summary, _ = _walk(_config(), None, harness)
    assert served == [150, 150, 150]
    assert summary["rows"] == 450


def test_reclaim_never_writes_the_forward_cursor(harness):
    """The invariant that makes re-mining safe: --walk re-reads ore the forward
    position has already covered, so writing that position would rewind the
    Scout past material it has walked."""
    _, saved = harness  # one list, shared by all three walks below

    _walk(_config(), 300, harness, cursor_key=None)
    assert saved == [], "a reclaim walk must touch no position at all"

    _walk(_config(), 300, harness, cursor_key="forward")
    assert saved and all("forward" in w for w in saved), "a pass advances forward"

    saved.clear()
    _walk(_config(), 300, harness, cursor_key="backfill")
    assert saved and all("backfill" in w for w in saved), (
        "a top-up writes the backfill position and must never write forward — "
        "that would rewind coverage of new ore to somewhere in the archive"
    )


def test_backfill_stops_at_the_forward_position(harness):
    """Catching up means the corpus has been re-mined once. Looping would
    silently re-bill the whole archive every time it came around."""
    served, _ = harness
    summary, _ = _walk(_config(), 300, harness, cursor_key="backfill", stop_at=200)
    assert summary["rows"] == 200, "must not read past where forward stood"
