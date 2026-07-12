"""Cursor-free sources — the Scout's free-roam side (NEWSROOM: only log
coverage is linear; every other source is temporally bidirectional).

v1 grazes one queryable seam: agent_decisions. The story-worthiness heuristic
is literal SQL — "a story where two agents interact is a sequence whose rows
span more than one agent_name." Span is a WEIGHT handed to synthesis, never a
filter: the recent single-agent sequences ride along too (the backup note was
single-actor and shipped first).
"""
from __future__ import annotations


def cross_agent_sequences(conn, span_limit: int = 6, recent_limit: int = 4) -> list[dict]:
    """Top sequences by agent span, plus the most recent regardless of span."""
    seqs: dict[str, dict] = {}
    with conn.cursor() as cur:
        for order_by, limit in (
            ("span DESC, last_seen DESC", span_limit),
            ("last_seen DESC", recent_limit),
        ):
            cur.execute(
                f"""
                SELECT workflow_sequence_id::text,
                       COUNT(DISTINCT agent_name) AS span,
                       ARRAY_AGG(DISTINCT agent_name) AS agents,
                       COUNT(*) AS steps,
                       MAX(decision_timestamp) AS last_seen
                FROM agent_decisions
                WHERE workflow_sequence_id IS NOT NULL
                GROUP BY workflow_sequence_id
                ORDER BY {order_by}
                LIMIT %s
                """,
                (limit,),
            )
            for seq_id, span, agents, steps, last_seen in cur.fetchall():
                seqs.setdefault(
                    seq_id,
                    {
                        "sequence_id": seq_id,
                        "agent_span": span,
                        "agents": list(agents),
                        "steps": steps,
                        "last_seen": str(last_seen),
                    },
                )
        # A few reasons per sequence — the `reason` column is where the why lives.
        for entry in seqs.values():
            cur.execute(
                """
                SELECT agent_name, LEFT(routing_reason, 200)
                FROM agent_decisions
                WHERE workflow_sequence_id = %s AND routing_reason IS NOT NULL
                ORDER BY step_number
                LIMIT 4
                """,
                (entry["sequence_id"],),
            )
            entry["sample_reasons"] = [f"{a}: {r}" for a, r in cur.fetchall()]
    return sorted(seqs.values(), key=lambda e: (-e["agent_span"], e["last_seen"]), reverse=False)
