-- =====================================================
-- 005 — jewel provenance: a jewel may come from somewhere other than a transcript
-- =====================================================
-- 004 created scout_jewel to stop throwing away mined material. It succeeded for
-- one of the Scout's six sources and silently excluded the other five.
--
-- The constraint is `seq BIGINT NOT NULL REFERENCES scout_session_log(seq)`. A
-- jewel cannot exist without pointing at a transcript row, so material mined
-- from git history, the design docs, the sysadmin ledger, the ops calendar, the
-- marketing survey or agent_decisions can inform a jewel's note but can never
-- BE one — there is no field in which to record where it came from.
--
-- Nobody decided this. The NOT NULL FK is an anti-hallucination control: the
-- walker cites seqs from the page it was shown, and persist() drops anything
-- off-page so a fabricated citation cannot land. That control is correct and is
-- kept. Its side effect — that the schema's only provenance field is a
-- transcript position — is what turned a soft prompt-level preference ("session
-- logs are the primary ore") into a hard structural one. See
-- docs/uzelhub-crew/jewels-are-transcript-only-2026-09-03.md.
--
-- The irony worth recording: 004's own header calls this table "a PUBLISHED
-- INTERFACE" whose anticipated consumers are "a directed hunt on a named topic,
-- a monthly arc digest". A directed hunt is exactly the commissioned-prospecting
-- pathway, and against a transcript-only jewel layer it would be blind to five
-- of six sources while believing it had searched the box.
--
-- TIMING: this lands before the corpus was mined, not after. scout_jewel holds
-- 58 rows from a single date (2026-07-12) against 14,852 ingested turns. The
-- full re-mine the retool made affordable (~95 pages, ~$1) has not been run. So
-- there is almost nothing to migrate and no legacy of transcript-only jewels to
-- live with — mine once, after this, over everything.
--
-- WHAT DOES NOT CHANGE: the pineapple ban from 004. These are PROVENANCE
-- columns — where a jewel came from — never DISPOSITION. Still no lead_id, no
-- became_lead, no status, no score. The Scout must not learn which findings an
-- editor liked, and the ban stays structural rather than disciplinary.
--
-- WHAT THIS MIGRATION GIVES UP, STATED PLAINLY: for non-transcript jewels there
-- is no foreign key to validate against, because a git sha or a file path has no
-- table to reference. The DB-level anti-hallucination guarantee therefore covers
-- transcript rows only. persist() MUST supply the equivalent check for other
-- sources — validate source_ref against the candidate set actually shown to the
-- walker, exactly as the seq allowlist does today. This migration is not safe to
-- use until that code exists.

BEGIN;

ALTER TABLE scout_jewel
    ADD COLUMN source_type VARCHAR(24) NOT NULL DEFAULT 'transcript',
    ADD COLUMN source_ref  TEXT;

-- The 58 existing rows are all transcript-mined; the DEFAULT above labels them
-- correctly, so no backfill statement is needed.

-- seq stays a FK (still enforced when present) but is no longer mandatory.
ALTER TABLE scout_jewel ALTER COLUMN seq DROP NOT NULL;

-- Exactly one anchor, and it must match the declared type. This is what stops
-- the two provenance models blurring into "sometimes both, sometimes neither".
ALTER TABLE scout_jewel ADD CONSTRAINT jewel_anchor_matches_type CHECK (
    (source_type =  'transcript' AND seq IS NOT NULL AND source_ref IS NULL)
 OR (source_type <> 'transcript' AND seq IS     NULL AND source_ref IS NOT NULL)
);

-- UNIQUE (seq, kind, note) cannot survive a nullable seq: Postgres treats NULLs
-- as distinct, so every non-transcript jewel would be trivially unique and the
-- idempotency 004 relies on would silently vanish for five of six sources.
-- COALESCE gives one comparable anchor key across both provenance models.
ALTER TABLE scout_jewel DROP CONSTRAINT scout_jewel_seq_kind_note_key;

CREATE UNIQUE INDEX uq_jewel_anchor
    ON scout_jewel (source_type, COALESCE(seq::text, source_ref), kind, note);

CREATE INDEX idx_jewel_source_type ON scout_jewel(source_type);

COMMENT ON COLUMN scout_jewel.source_type IS
    'Where the jewel was mined from: transcript | git | doc | ledger | calendar '
    '| survey | agent_decisions. Deliberately NOT an enum or FK lookup — the '
    'Scout''s source catalog is meant to grow by dropping a reader in, and a '
    'curated vocabulary here would make adding a source a schema migration.';
COMMENT ON COLUMN scout_jewel.source_ref IS
    'The pointer for non-transcript jewels: a git sha, a repo-relative path with '
    'line range, a calendar UID, an agent_decisions sequence id. NULL for '
    'transcript jewels, which anchor on seq instead. No FK is possible here, so '
    'persist() carries the anti-hallucination check the seq FK provides.';
COMMENT ON COLUMN scout_jewel.session_date IS
    'The DATE OF THE SOURCE MATERIAL, whatever the source — the ore row''s '
    'session_date for transcripts, the commit date for git, and so on. Every '
    'consumer slices by time and needs one comparable column. NAMING DEBT '
    '(2026-09-03): the name says "session" because transcripts were the only '
    'source when 004 was written. Kept rather than renamed because consumers '
    'filter on it and the cluster has no per-table restore; read it as '
    'source_date.';

INSERT INTO schema_version (version_number, description) VALUES
('1.4.0',
 'scout_jewel provenance — a jewel may be anchored to a non-transcript source, '
 'so the other five Scout sources can contribute mined material '
 '(docs/uzelhub-crew/jewels-are-transcript-only-2026-09-03.md)');

COMMIT;
