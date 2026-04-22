"""
Corpus cohesion graph — stores post descriptors and ranks link candidates.

No graph DB, no embeddings. Just JSONB descriptors on each post row and
SQL queries over them. Upgrade path exists if topic overlap proves too
coarse, but 2-3 posts/week likely never needs it.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid runtime dep on agents module during isolated tests
    from agents.marketer_agent import LinkCandidate, PostDescriptor


def store_descriptor(conn, post_id: int, descriptor: "PostDescriptor") -> None:
    """Persist the JSON descriptor on the post row.

    Assumes a `posts` table with a `descriptor JSONB` column created in the
    schema migration landed in PR 2.
    """
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE posts SET descriptor = %s WHERE post_id = %s",
            (asdict(descriptor), post_id),
        )
        conn.commit()


def rank_link_candidates(
    conn,
    descriptor: "PostDescriptor",
    exclude_post_id: int | None = None,
    limit: int = 10,
) -> list["LinkCandidate"]:
    """Return posts ranked by tag-overlap with the given descriptor.

    Scoring is deterministic: count of topic/concept/system terms the
    candidate shares with the source descriptor, weighted toward concepts.
    Sorted descending, ties broken by recency.
    """
    from agents.marketer_agent import LinkCandidate  # local import to avoid cycle

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                post_id,
                slug,
                title,
                descriptor,
                (
                    (SELECT COUNT(*) FROM jsonb_array_elements_text(descriptor->'concepts') e
                       WHERE e = ANY(%(concepts)s)) * 2
                  + (SELECT COUNT(*) FROM jsonb_array_elements_text(descriptor->'topics') e
                       WHERE e = ANY(%(topics)s))
                  + (SELECT COUNT(*) FROM jsonb_array_elements_text(descriptor->'systems_mentioned') e
                       WHERE e = ANY(%(systems)s))
                ) AS overlap
            FROM posts
            WHERE descriptor IS NOT NULL
              AND (%(exclude)s IS NULL OR post_id <> %(exclude)s)
            ORDER BY overlap DESC, created_at DESC
            LIMIT %(limit)s
            """,
            {
                "concepts": descriptor.concepts,
                "topics": descriptor.topics,
                "systems": descriptor.systems_mentioned,
                "exclude": exclude_post_id,
                "limit": limit,
            },
        )
        rows = cur.fetchall()

    candidates: list[LinkCandidate] = []
    max_overlap = rows[0][4] if rows and rows[0][4] else 1
    for row in rows:
        post_id, slug, title, _descriptor, overlap = row
        if not overlap:
            continue
        candidates.append(
            LinkCandidate(
                post_id=post_id,
                slug=slug,
                title=title,
                overlap_score=overlap / max_overlap if max_overlap else 0.0,
            )
        )
    return candidates
