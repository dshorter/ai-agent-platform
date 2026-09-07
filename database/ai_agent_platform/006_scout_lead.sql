-- =====================================================
-- 006 — the leads ledger becomes tables, and the pineapple rule becomes a grant
-- =====================================================
-- ADR-003 settled the direction on 2026-09-04 and deferred the work. This is the
-- schema half of it, and ONLY the schema half. Nothing in the crew reads these
-- tables yet: `pipelines/scout/state/leads.yaml` is still the live ledger, and
-- the 17 leads in it are not migrated here. Applying this file changes no
-- behaviour — see WHEN IS THIS SAFE TO USE, at the bottom.
--
-- WHY THE DATABASE, IN ONE FACT. The Scout already cannot run without Postgres:
-- every verb opens a connection, and scout_jewel, scout_session_log and
-- agent_decisions all live in this cluster. A file-based ledger therefore buys
-- no independence from the database — it only means the newsroom's state lives
-- in two places under two different sets of guarantees. Every argument for flat
-- files rested on an availability property the system does not have.
--
-- THE REASON THAT MATTERS MOST IS NOT COST OR ERGONOMICS. It is this:
--
--   The pineapple rule — the Scout learns navigation, never taste — is enforced
--   today by a hand-rolled parser's INCOMPLETENESS. `leads.load_pitched` matches
--   two patterns and has none for `status`. That is genuinely clever, and it is
--   a safety property that depends on nobody ever improving a parser.
--
-- Below, it depends on nothing. `scout_role` is granted SELECT on a view that
-- has no status column, and INSERT on a COLUMN LIST that excludes status. It
-- cannot read a disposition because it is not permitted to, and it cannot file a
-- lead as anything but `new` because the column it would have to write is not
-- one of the columns it may write. spec-scout.md §Filing says "the Scout never
-- edits or removes a lead"; here that sentence is the absence of an UPDATE and a
-- DELETE grant rather than a promise about a code path.
--
-- WHAT CHANGES NAME FROM THE ADR's SKETCH. `register` becomes `type` (the word
-- is reserved for the tonal band — GLOSSARY) and `sources` becomes `citations`.
-- The rename was the plan's, and doing it here rather than after is the whole
-- benefit of the migration not having happened yet.
--
-- WHAT THIS GIVES UP, STATED PLAINLY. Hand-editing the queue in an editor is
-- gone; `lead_mark` already exists because freehand editing was discouraged, but
-- the loss is real. And a lead's provenance stops being greppable in a file that
-- a human can read without a client — which is exactly the doctrine ("external,
-- inspectable, warm-bootable") that ADR-003 found had been applied outside the
-- case it was written for. That rule was about the CURSOR and the MAP — learned
-- state, where the worry is a rut you cannot see. A ledger is records, and psql
-- is inspectable.
--
-- WHAT DOES NOT CHANGE: everything 004 and 005 said about scout_jewel. No
-- disposition ever travels back to the mining layer. These tables are the
-- Editor's side of the wall, and the wall is what the grants below build.

BEGIN;

-- --------------------------------------------------------------------------
-- The two vocabularies, curated behind foreign keys.
--
-- Same pattern as `decision_types` (001), and for the same stated reason:
-- adding one is a decision, not a detail (AGENTS.md §Shared surfaces). It is
-- also what spec-content-types.md already says out loud — "a new type is a new
-- row here plus a voice profile and a sink, never a new agent" — so a row is
-- the honest shape. A CHECK constraint would have put the same list in a third
-- place that only a migration can edit.
-- --------------------------------------------------------------------------

CREATE TABLE content_type (
    type VARCHAR(16) PRIMARY KEY,
    note TEXT NOT NULL
);

INSERT INTO content_type (type, note) VALUES
('ticker',     'the box''s activity in verbs, a rolling pulse; sink is the site-wide masthead'),
('newsletter', 'the week''s digest, the Director''s weekly report made public; sink is apex /newsletter/'),
('note',       'field notes, platform self-awareness first and war stories second; sink is apex /notes/'),
('blog',       'narrative for developers, deep dives; sink is Ghost and Ghost is canonical'),
('paper',      'a white paper or case study; the sink is deliberately unplaced');

-- The lifecycle as data. `from_state` is the set a lead may arrive from and
-- `actor` is the hat that must be worn to make the move — both were a Python
-- dict in lead_mark.TRANSITIONS, enforced at exactly the call sites that
-- remembered to import it.
--
-- `spiked` and `rejected` are deliberately distinct verdicts, not one state
-- with two names: spiking says the story was never worth telling, rejecting
-- says it was and the draft failed it. Only the second is a signal about the
-- Writer, and keeping them apart is what lets this table answer "how often does
-- the Writer produce something unusable" — the metric that says whether the
-- voice bottle is maturing. The gap that made `rejected` impossible for months
-- would have surfaced here as a missing row, which is the argument.
CREATE TABLE lead_state (
    state      VARCHAR(16) PRIMARY KEY,
    from_state VARCHAR(16)[] NOT NULL,
    actor      VARCHAR(32)   NOT NULL,
    terminal   BOOLEAN       NOT NULL DEFAULT FALSE
);

INSERT INTO lead_state (state, from_state, actor, terminal) VALUES
('new',       '{}',                 'scout',     FALSE),
('claimed',   '{new}',              'editor',    FALSE),
('spiked',    '{new,claimed}',      'editor',    TRUE),
('drafted',   '{claimed,drafted}',  'writer',    FALSE),
('approved',  '{drafted}',          'editor',    FALSE),
('rejected',  '{drafted}',          'editor',    TRUE),
('published', '{approved}',         'publisher', TRUE);

-- --------------------------------------------------------------------------
-- The ledger itself.
-- --------------------------------------------------------------------------

CREATE TABLE scout_lead (
    -- The slug is the ledger key AND the published URL, across ~53 call sites.
    -- It is never re-keyed, which is exactly what a primary key means.
    id         TEXT PRIMARY KEY,
    filed      DATE        NOT NULL,
    type       VARCHAR(16) NOT NULL REFERENCES content_type(type),
    agent_span INT         NOT NULL DEFAULT 1 CHECK (agent_span >= 1),
    pitch      TEXT        NOT NULL,
    why_now    TEXT        NOT NULL,
    -- Publishable text, so a gated source needs an opaque form BEFORE it is
    -- ever mined (AGENTS.md §Open questions). An array rather than a blob
    -- because a citation is one pointer and consumers want them one at a time.
    citations  TEXT[]      NOT NULL DEFAULT '{}',
    model      VARCHAR(64) NOT NULL,
    redaction  VARCHAR(16) NOT NULL DEFAULT 'required',
    status     VARCHAR(16) NOT NULL DEFAULT 'new' REFERENCES lead_state(state)
);

CREATE INDEX idx_lead_status ON scout_lead(status);
CREATE INDEX idx_lead_filed  ON scout_lead(filed);

-- The lifecycle's stamps, which accumulate as lines in a YAML block today.
-- As rows they are queryable, so time-to-publish reads off a join instead of a
-- parser — and the primary key makes a transition idempotent and unrepeatable
-- by construction.
CREATE TABLE scout_lead_stamp (
    lead_id  TEXT        NOT NULL REFERENCES scout_lead(id),
    state    VARCHAR(16) NOT NULL REFERENCES lead_state(state),
    stamped  DATE        NOT NULL,
    actor    VARCHAR(32) NOT NULL,
    -- Concordance is only meaningful against HUMAN verdicts. On 2026-08-03 it
    -- was found scoring 6/6 against leads an agent session had claimed as
    -- `--by editor`: a machine agreeing with a machine that had read its own
    -- proposals. Roles say which hat was worn; this says whose head it was on.
    by_agent BOOLEAN     NOT NULL DEFAULT FALSE,
    PRIMARY KEY (lead_id, state)
);

-- --------------------------------------------------------------------------
-- Forward-only transitions, and the actor that may make them.
-- --------------------------------------------------------------------------

CREATE FUNCTION scout_lead_transition() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    legal VARCHAR(16)[];
BEGIN
    IF NEW.status = OLD.status THEN
        RETURN NEW;
    END IF;
    SELECT from_state INTO legal FROM lead_state WHERE state = NEW.status;
    IF NOT (OLD.status = ANY (legal)) THEN
        RAISE EXCEPTION
            'lead %: % -> % is not a legal transition (legal from: %)',
            OLD.id, OLD.status, NEW.status, legal
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER scout_lead_forward_only
    BEFORE UPDATE OF status ON scout_lead
    FOR EACH ROW EXECUTE FUNCTION scout_lead_transition();

CREATE FUNCTION scout_lead_stamp_actor() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    expected VARCHAR(32);
BEGIN
    SELECT actor INTO expected FROM lead_state WHERE state = NEW.state;
    IF NEW.actor <> expected THEN
        RAISE EXCEPTION
            'lead %: a % stamp is the %''s to make, not the %''s',
            NEW.lead_id, NEW.state, expected, NEW.actor
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER scout_lead_stamp_actor_matches
    BEFORE INSERT OR UPDATE ON scout_lead_stamp
    FOR EACH ROW EXECUTE FUNCTION scout_lead_stamp_actor();

-- --------------------------------------------------------------------------
-- The dedup memory, as the only thing the Scout may read.
-- --------------------------------------------------------------------------

-- Python's `str.rfind`, so the digest below can be the same cut as
-- `leads._digest` rather than a near-miss. Returns a 0-based index, or -1.
CREATE FUNCTION scout_rfind(haystack TEXT, needle TEXT) RETURNS INT
LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
    p INT := strpos(reverse(haystack), reverse(needle));
BEGIN
    IF p = 0 THEN
        RETURN -1;
    END IF;
    RETURN length(haystack) - p - length(needle) + 1;
END;
$$;

-- The first SENTENCE of a pitch, or a word-boundary cut, whichever comes first.
-- Not `left()`: a cut mid-thought reads as a short pitch rather than a digest,
-- and the ellipsis is what tells the model it is looking at one.
-- Mirrors pipelines/scout/leads._digest exactly; the two are one rule in two
-- languages until the store module deletes the Python side.
CREATE FUNCTION scout_pitch_digest(pitch TEXT, limit_chars INT DEFAULT 240)
RETURNS TEXT LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
    body TEXT := btrim(pitch);
    win  TEXT;
    stop INT;
    cut  INT;
BEGIN
    IF limit_chars <= 0 OR length(body) <= limit_chars THEN
        RETURN body;
    END IF;
    win  := left(body, limit_chars);
    stop := GREATEST(scout_rfind(win, '. '),
                     scout_rfind(win, '? '),
                     scout_rfind(win, '! '));
    IF stop >= limit_chars / 3 THEN          -- a sentence ended in range
        RETURN left(win, stop + 1);
    END IF;
    cut := scout_rfind(win, ' ');
    IF cut > 0 THEN
        win := left(win, cut);
    END IF;
    RETURN rtrim(win, ',;:—- ') || ' …';
END;
$$;

-- 240 characters, measured 2026-09-04: the full-text payload was 279,744 chars
-- over 477 leads and this is 130,815 — 53% off the dominant term in every
-- synthesis call, and off its growth rate permanently, with every digest still
-- a complete first sentence.
--
-- It is a constant here where SCOUT_PITCH_DIGEST_CHARS is a knob in .env, and
-- that is the one thing this view takes away. A parameterised digest would have
-- to be a SECURITY DEFINER function, which is a second privilege surface to
-- audit for a value that has not moved since it was measured. If it ever needs
-- to vary per run, that is the change — and it needs the same care this view's
-- ownership needs, below.
--
-- **This view MUST NOT be recreated WITH (security_invoker = true).** Postgres
-- runs a view with its owner's rights by default, which is the entire mechanism
-- that lets scout_role read this without reading scout_lead. Flipping that
-- option would not fail — it would silently start returning permission errors
-- to the Scout, and the fix that "works" is a SELECT grant on the base table,
-- which is the pineapple rule quietly deleted.
CREATE VIEW scout_pitched AS
    SELECT id, scout_pitch_digest(pitch) AS pitch FROM scout_lead;

-- --------------------------------------------------------------------------
-- The grants. This is the migration's reason for existing.
-- --------------------------------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'scout_role') THEN
        -- No password: the cluster is container-local and every existing DSN
        -- (`postgresql://hvac_user@localhost:5432/…`) already relies on that.
        -- Minting a credential here would put a secret in a tracked file to
        -- solve a problem this deployment does not have.
        CREATE ROLE scout_role LOGIN;
    END IF;
END
$$;

GRANT CONNECT ON DATABASE ai_agent_platform TO scout_role;
GRANT USAGE   ON SCHEMA public TO scout_role;

-- Read: the digest view, and nothing else. No SELECT on scout_lead, none on
-- scout_lead_stamp. A status cannot reach the Scout because there is no
-- statement it may write that returns one.
GRANT SELECT ON scout_pitched TO scout_role;

-- Write: append only, and NOT the status column. The default 'new' is therefore
-- the only status the Scout can file under — not by convention, by privilege.
-- No UPDATE and no DELETE: "the Scout never edits or removes a lead" stops
-- being a sentence in a spec.
GRANT INSERT (id, filed, type, agent_span, pitch, why_now, citations, model,
              redaction)
    ON scout_lead TO scout_role;

COMMENT ON VIEW scout_pitched IS
    'The dedup memory: id plus a digested pitch, status-blind by construction. '
    'The only relation scout_role may read. Owner''s-rights view — see 006.';
COMMENT ON TABLE scout_lead IS
    'The Editor''s queue and the record of what ambient prospecting found. '
    'The Scout may INSERT (minus status) and may not read it back.';
COMMENT ON COLUMN scout_lead.citations IS
    'Publishable text. A gated source needs an opaque reference before it is '
    'mined, not after — once written, those refs are in every lead that cites '
    'the material.';

INSERT INTO schema_version (version_number, description) VALUES
('1.5.0',
 'scout_lead, scout_lead_stamp, lead_state and content_type — the leads ledger '
 'moves from hand-parsed YAML to tables, and the pineapple rule becomes a '
 'column grant (ADR-003). Schema only: no reader or writer uses these yet.');

COMMIT;

-- =====================================================
-- WHEN IS THIS SAFE TO USE
-- =====================================================
-- Applying it is safe now — every object is new, nothing existing is altered,
-- and `apply-006-scout-lead.sh` verifies the grants and tears the whole thing
-- back out if they do not hold.
--
-- USING it needs two things this file does not provide:
--
--   1. A store module, and the 17 modules that read or write leads.yaml moved
--      onto it. Until then leads.yaml remains the ledger and these tables stay
--      empty. Two live ledgers would be worse than either one.
--   2. The Scout connecting AS scout_role (its own DSN), because a grant that
--      the process never connects under enforces nothing. hvac_user owns these
--      tables and can read everything; the wall exists only for the role that
--      sits behind it.
--
-- The cutover also has to carry the 17 live leads across, and the cluster has
-- no per-table restore point (AGENTS.md §Shared surfaces) — so it takes a dump
-- first, exactly as 005 did.
