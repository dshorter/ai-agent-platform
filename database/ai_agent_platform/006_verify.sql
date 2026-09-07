-- =====================================================
-- 006 — self-verification. Runs in a transaction that is ALWAYS rolled back.
-- =====================================================
-- Every check here is a claim 006's header makes. A migration that installs a
-- privilege wall and never tries to climb it has shipped a comment, not a
-- control — and the two failures this estate keeps writing down (a guard that
-- covered one path, a metric scored against the wrong actor) were both of
-- exactly that shape.
--
-- Run with ON_ERROR_STOP=1: any RAISE below exits non-zero and the apply script
-- tears the migration back out.

\set ON_ERROR_STOP on

BEGIN;

-- --- the vocabularies are seeded, and are the ones the specs name -----------

DO $$
DECLARE
    types TEXT[];
    states TEXT[];
BEGIN
    SELECT array_agg(type ORDER BY type) INTO types FROM content_type;
    IF types <> ARRAY['blog','newsletter','note','paper','ticker'] THEN
        RAISE EXCEPTION 'content_type is not the five words: %', types;
    END IF;

    SELECT array_agg(state ORDER BY state) INTO states FROM lead_state;
    IF states <> ARRAY['approved','claimed','drafted','new','published',
                       'rejected','spiked'] THEN
        RAISE EXCEPTION 'lead_state is not the seven states: %', states;
    END IF;
    RAISE NOTICE 'ok: five types, seven states';
END
$$;

-- --- the digest is the same cut leads._digest makes -------------------------

DO $$
DECLARE
    long_pitch TEXT := repeat('a', 98) || '. ' || repeat('b', 300);
BEGIN
    IF scout_pitch_digest('short enough to pass through') <>
       'short enough to pass through' THEN
        RAISE EXCEPTION 'a pitch under the limit must come back whole';
    END IF;
    -- The first sentence ends at 98, past limit/3, so the cut lands there and
    -- carries the full stop and no ellipsis.
    IF scout_pitch_digest(long_pitch) <> repeat('a', 98) || '.' THEN
        RAISE EXCEPTION 'digest did not cut on the sentence: %',
            scout_pitch_digest(long_pitch);
    END IF;
    -- No sentence in range: a word-boundary cut, marked as a digest.
    IF right(scout_pitch_digest(repeat('word ', 200)), 2) <> ' …' THEN
        RAISE EXCEPTION 'a word-boundary cut must be marked with an ellipsis';
    END IF;
    RAISE NOTICE 'ok: the digest cuts on a sentence, then on a word';
END
$$;

-- --- the lifecycle is forward-only, and actor-matched -----------------------

INSERT INTO scout_lead (id, filed, type, pitch, why_now, citations, model)
VALUES ('verify-006-probe', CURRENT_DATE, 'note', 'A probe.', 'Now.',
        ARRAY['session 00000000 turns 1-2'], 'verify');

DO $$
BEGIN
    BEGIN
        UPDATE scout_lead SET status = 'published' WHERE id = 'verify-006-probe';
        RAISE EXCEPTION 'FORWARD-ONLY BROKEN: new -> published was allowed';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'ok: new -> published refused';
    END;

    UPDATE scout_lead SET status = 'claimed' WHERE id = 'verify-006-probe';

    BEGIN
        INSERT INTO scout_lead_stamp (lead_id, state, stamped, actor)
        VALUES ('verify-006-probe', 'claimed', CURRENT_DATE, 'writer');
        RAISE EXCEPTION 'ACTOR MATCH BROKEN: the writer claimed a lead';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'ok: a claim is the editor''s to make';
    END;

    INSERT INTO scout_lead_stamp (lead_id, state, stamped, actor, by_agent)
    VALUES ('verify-006-probe', 'claimed', CURRENT_DATE, 'editor', TRUE);
    RAISE NOTICE 'ok: the editor may claim, and the agent flag is recorded';
END
$$;

-- --- the wall, from behind it ----------------------------------------------
-- SET ROLE rather than a fresh login: it exercises the same privilege check
-- without depending on pg_hba, so this verification works the same on a box
-- where the role has no way to authenticate yet.

SET ROLE scout_role;

DO $$
DECLARE
    n INT;
BEGIN
    SELECT count(*) INTO n FROM scout_pitched;
    RAISE NOTICE 'ok: scout_role reads the dedup view (% row(s))', n;

    BEGIN
        PERFORM 1 FROM scout_lead LIMIT 1;
        RAISE EXCEPTION 'PINEAPPLE BROKEN: scout_role can read scout_lead';
    EXCEPTION WHEN insufficient_privilege THEN
        RAISE NOTICE 'ok: scout_role cannot read scout_lead';
    END;

    BEGIN
        PERFORM 1 FROM scout_lead_stamp LIMIT 1;
        RAISE EXCEPTION 'PINEAPPLE BROKEN: scout_role can read the stamps';
    EXCEPTION WHEN insufficient_privilege THEN
        RAISE NOTICE 'ok: scout_role cannot read scout_lead_stamp';
    END;

    BEGIN
        INSERT INTO scout_lead (id, filed, type, pitch, why_now, model, status)
        VALUES ('verify-006-status', CURRENT_DATE, 'note', 'p', 'w', 'verify',
                'claimed');
        RAISE EXCEPTION 'PINEAPPLE BROKEN: scout_role set a status';
    EXCEPTION WHEN insufficient_privilege THEN
        RAISE NOTICE 'ok: scout_role may not write the status column';
    END;

    INSERT INTO scout_lead (id, filed, type, pitch, why_now, model)
    VALUES ('verify-006-filed', CURRENT_DATE, 'note', 'p', 'w', 'verify');
    RAISE NOTICE 'ok: scout_role may file a lead';

    BEGIN
        UPDATE scout_lead SET pitch = 'edited' WHERE id = 'verify-006-filed';
        RAISE EXCEPTION 'BROKEN: scout_role edited a lead';
    EXCEPTION WHEN insufficient_privilege THEN
        RAISE NOTICE 'ok: scout_role cannot edit a lead';
    END;

    BEGIN
        DELETE FROM scout_lead WHERE id = 'verify-006-filed';
        RAISE EXCEPTION 'BROKEN: scout_role deleted a lead';
    EXCEPTION WHEN insufficient_privilege THEN
        RAISE NOTICE 'ok: scout_role cannot remove a lead';
    END;
END
$$;

RESET ROLE;

-- Nothing this file wrote is kept. The probe rows exist only to be refused.
ROLLBACK;
