"""Director persistence — Postgres helpers.

Walking skeleton: just the `pipeline_runs` bookkeeping so each Director turn logs
under a real run (agent_decisions.run_id is an FK to pipeline_runs). The ledger
(dependencies + decisions-awaiting-Dan) will live here as it lands.
"""
from __future__ import annotations

import uuid


def create_run(conn, pipeline_name: str = "director") -> uuid.UUID:
    """Open a pipeline_runs row and return its run_id (the log task_id)."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO pipeline_runs (pipeline_name, status) "
            "VALUES (%s, 'running') RETURNING run_id",
            (pipeline_name,),
        )
        run_id = cur.fetchone()[0]
        conn.commit()
    return run_id


def complete_run(conn, run_id, status: str = "success") -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE pipeline_runs "
            "SET status = %s, completed_at = NOW(), "
            "    duration_ms = (EXTRACT(EPOCH FROM (NOW() - started_at)) * 1000)::int "
            "WHERE run_id = %s",
            (status, run_id),
        )
        conn.commit()
