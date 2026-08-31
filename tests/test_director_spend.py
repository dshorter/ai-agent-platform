"""The predictor-spend block injected into the Director's state.

The Director reports on the predictor's money; it must never be able to change
it, and it must degrade to silence rather than take the brief down with it.
"""

from __future__ import annotations

import sqlite3

import pytest

from pipelines.director import project_state


def _make_db(path, rows):
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date TEXT NOT NULL, stage TEXT NOT NULL, model TEXT NOT NULL,
            doc_id TEXT, input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL,
            cost_usd REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            billing_mode TEXT NOT NULL DEFAULT 'sync')""")
    conn.executemany(
        "INSERT INTO token_usage (run_date, stage, model, doc_id, input_tokens,"
        " output_tokens, cost_usd, billing_mode) VALUES (?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()


@pytest.fixture
def db_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(project_state, "_PREDICTOR_DB_DIR", tmp_path)
    return tmp_path


def _today():
    from datetime import date
    return date.today().isoformat()


class TestPredictorSpend:
    def test_reports_per_domain_and_total(self, db_dir):
        _make_db(db_dir / "film.db",
                 [(_today(), "extraction", "claude-sonnet-5", None, 10, 10, 3.00, "batch")])
        _make_db(db_dir / "semiconductors.db",
                 [(_today(), "synthesis", "claude-sonnet-5", None, 10, 10, 1.50, "sync")])
        out = project_state.predictor_spend()
        assert "film" in out and "$3.00" in out
        assert "semiconductors" in out and "$1.50" in out
        assert "$4.50" in out          # the total
        assert "actual dollars charged" in out

    def test_silent_when_there_is_nothing_to_report(self, db_dir):
        assert project_state.predictor_spend() == ""

    def test_missing_directory_is_not_an_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(project_state, "_PREDICTOR_DB_DIR", tmp_path / "nope")
        assert project_state.predictor_spend() == ""

    def test_database_without_the_table_is_skipped(self, db_dir):
        sqlite3.connect(db_dir / "empty.db").close()
        _make_db(db_dir / "film.db",
                 [(_today(), "synthesis", "claude-sonnet-5", None, 10, 10, 2.00, "sync")])
        out = project_state.predictor_spend()
        assert "film" in out
        assert "empty" not in out

    def test_unpriced_calls_are_surfaced_not_hidden(self, db_dir):
        _make_db(db_dir / "film.db", [
            (_today(), "extraction", "claude-sonnet-5", None, 10, 10, 1.00, "batch"),
            (_today(), "extraction", "mystery-model", None, 10, 10, None, "batch"),
        ])
        out = project_state.predictor_spend()
        assert "NO price on file" in out
        assert "incomplete" in out

    def test_connection_is_read_only(self, db_dir):
        """The Director must not be able to write to the predictor's books."""
        _make_db(db_dir / "film.db",
                 [(_today(), "synthesis", "claude-sonnet-5", None, 10, 10, 1.00, "sync")])
        project_state.predictor_spend()  # populates nothing, but proves the path
        conn = sqlite3.connect(f"file:{db_dir / 'film.db'}?mode=ro", uri=True)
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("UPDATE token_usage SET cost_usd = 999")
        conn.close()

    def test_included_in_gathered_state(self, db_dir, monkeypatch):
        _make_db(db_dir / "film.db",
                 [(_today(), "synthesis", "claude-sonnet-5", None, 10, 10, 7.25, "sync")])
        monkeypatch.setattr(project_state, "load_registry", lambda: [
            project_state.Project(name="x", path="/tmp", note="")])
        monkeypatch.setattr(project_state, "todos_digest", lambda: "(todos)")
        monkeypatch.setattr(project_state, "ledger", lambda: "")
        assert "PREDICTOR SPEND" in project_state.gather_state()
