-- =====================================================
-- 004 — scout_jewel: stop throwing away the mining
-- =====================================================
-- The Scout's walk extracts jewels from every page of ore it reads, hands them
-- to synthesis, and loses them when the process exits — they live in a local
-- list in pipelines/scout/run.py and are written nowhere. Measured 2026-08-21
-- (docs/uzelhub-crew/scout-mining-economics.md): ~1,645 jewels extracted across
-- 35 passes, and 73.3% of the corpus is cited by no lead at all. The expensive
-- cognitive work was done and the product discarded.
--
-- That is also why re-mining is unaffordable today. The walk is the cheap tier
-- (~$0.0105 per 150-row page; the whole 14,198-turn corpus is 95 pages, about a
-- dollar) but it cannot be run without also triggering the premium synthesis,
-- because the two are welded into one pass. Persisting the jewel layer is what
-- lets them come apart: once this table exists, synthesis is a CONSUMER of it
-- rather than a stage inside the walk, and a re-mine costs ~$1 instead of ~$200.
--
-- This table is a PUBLISHED INTERFACE, not Scout-private scratch. Later readers
-- (a directed hunt on a named topic, a monthly arc digest) query it instead of
-- re-reading transcripts, so a row has to make sense to something that was not
-- present when it was mined. That does NOT mean copying transcript text: every
-- jewel carries its seq, so (jewel JOIN scout_session_log) reconstructs the full
-- context for one indexed lookup. It means carrying the dimensions a consumer
-- slices on without a join.
--
-- WHAT IS DELIBERATELY ABSENT: any column describing what became of a jewel.
-- No lead_id, no became_lead, no status, no score. The Scout must never learn
-- which of its findings an editor liked — that is the pineapple rule, and this
-- table is the most tempting place in the system to break it. The ban is
-- structural rather than disciplinary: the columns do not exist, so no future
-- reader can filter on them by accident. Analysis that joins jewels to lead
-- outcomes is legitimate, belongs in tools/, and is run by a human.

BEGIN;

CREATE TABLE scout_jewel (
    id           BIGSERIAL PRIMARY KEY,
    seq          BIGINT NOT NULL REFERENCES scout_session_log(seq),
    kind         VARCHAR(16) NOT NULL,   -- principle|correction|reframe|decision|aha
    note         TEXT NOT NULL,          -- the walker's one tight sentence
    session_date DATE NOT NULL,          -- denormalized from the ore row (see below)
    run_id       UUID NOT NULL REFERENCES pipeline_runs(run_id),
    walk_model   VARCHAR(64) NOT NULL,
    found_at     TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Exact re-finding is idempotent; a genuinely differently-worded finding
    -- from a later run still lands. Imperfect ON PURPOSE — near-duplicate
    -- phrasings across runs survive, and collapsing them is the consumer's
    -- problem. A stricter key would silently drop real second-run findings,
    -- which is the worse failure: this table's whole reason for existing is
    -- that dropping mined material is expensive.
    UNIQUE (seq, kind, note)
);

-- session_date is denormalized from scout_session_log deliberately. It is
-- immutable, and every anticipated consumer slices by time — a monthly digest
-- filters on it constantly, a topic hunt bounds by period. Paying a join for an
-- unchanging date on every such query is the wrong trade.
CREATE INDEX idx_jewel_date ON scout_jewel(session_date);
CREATE INDEX idx_jewel_seq  ON scout_jewel(seq);
CREATE INDEX idx_jewel_run  ON scout_jewel(run_id);
CREATE INDEX idx_jewel_kind ON scout_jewel(kind);

COMMENT ON TABLE scout_jewel IS
    'Scout mining output — one row per jewel the walk extracted. A published '
    'interface: later agents query it instead of re-reading transcripts. '
    'Carries NO disposition column, by design (the pineapple rule).';
COMMENT ON COLUMN scout_jewel.run_id IS
    'The pipeline_runs row whose walk found it. A re-walk is a new mining run, '
    'not a correction — jewels accumulate, nothing is superseded, and comparing '
    'two runs over the same ore is how a plate-size change gets verified.';
COMMENT ON COLUMN scout_jewel.session_date IS
    'Denormalized from scout_session_log.session_date — immutable, and every '
    'consumer slices on it.';
COMMENT ON COLUMN scout_jewel.walk_model IS
    'The model that mined it. The walk tier is an env var and will change; a '
    'jewel is not interpretable without knowing what produced it.';

INSERT INTO schema_version (version_number, description) VALUES
('1.3.0',
 'scout_jewel — persist the Scout''s mining output so walk and synthesis can '
 'come apart (docs/uzelhub-crew/scout-retool.md §1)');

COMMIT;
