-- =====================================================
-- 002 — Scout ingestion: Claude Code session transcripts
-- =====================================================
-- The Scout's primary ore (NEWSROOM.md §"The Scout's sources"): session logs
-- ingested one row per turn. The table is a *cursor substrate* — the Scout's
-- coverage walk pages through it by keyset, never OFFSET.
--
-- `seq` is the physically append-only realization of the logical
-- (date, session_id, turn) ordering: a session resumed days later lands its
-- new turns at the tail of `seq`, so the forward-only coverage walk still
-- sees them (a (date, session_id, turn) keyset would skip behind the
-- watermark). The cursor itself lives OUTSIDE the db (the Scout's state dir)
-- — external, inspectable, warm-bootable; reset it to re-scan.

CREATE TABLE scout_session_log (
    seq BIGSERIAL PRIMARY KEY,          -- ingest order; the coverage cursor keys on this
    session_id VARCHAR(64) NOT NULL,    -- session file stem (uuid)
    session_date DATE NOT NULL,
    turn INT NOT NULL,                  -- line number in the session JSONL (stable; gaps fine)
    role VARCHAR(12) NOT NULL,          -- 'human' | 'assistant'
    turn_type VARCHAR(12) NOT NULL,     -- 'query' | 'progress' | 'final'
    text TEXT NOT NULL,                 -- raw, verbatim — never overwritten
    text_clean TEXT,                    -- light-cleaned human turns; raw stays alongside
    scratchpad TEXT,                    -- the Scout's own opaque arc notes; NOTHING downstream parses this
    ingested_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (session_id, turn)           -- re-ingest is idempotent (ON CONFLICT DO NOTHING)
);

CREATE INDEX idx_scout_log_session ON scout_session_log(session_id, turn);
CREATE INDEX idx_scout_log_date ON scout_session_log(session_date);

COMMENT ON TABLE scout_session_log IS 'Scout ore: Claude Code session transcripts, one row per turn (NEWSROOM §Scout sources)';
COMMENT ON COLUMN scout_session_log.seq IS 'Append-only ingest order — the coverage walk''s keyset cursor';
COMMENT ON COLUMN scout_session_log.scratchpad IS 'Scout-opaque free text (arc breadcrumbs). Contract: no downstream reader parses it as structure';

INSERT INTO schema_version (version_number, description) VALUES
('1.1.0', 'scout_session_log — Scout ingestion of Claude Code session transcripts (NEWSROOM v1)');
