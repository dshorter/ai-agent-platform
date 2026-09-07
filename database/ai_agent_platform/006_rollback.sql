-- =====================================================
-- 006 — the deliberate teardown
-- =====================================================
-- Run by `apply-006-scout-lead.sh` when verification fails, and runnable by
-- hand if the migration is ever unwanted.
--
-- **This is the rollback, not a restore.** The cluster has no per-table restore
-- point, so undoing 006 by reloading a dump would destroy everything written to
-- ai_agent_platform since the dump was taken — every agent_decisions row, every
-- jewel from a walk that ran in between. Every object 006 creates is NEW, so a
-- precise DROP is both sufficient and the only safe shape. The dump the apply
-- script takes first is the backstop for the case this file cannot handle, not
-- the normal path.
--
-- Safe to run when 006 was never applied: every statement is IF EXISTS.

BEGIN;

DROP VIEW IF EXISTS scout_pitched;

DROP TRIGGER IF EXISTS scout_lead_stamp_actor_matches ON scout_lead_stamp;
DROP TRIGGER IF EXISTS scout_lead_forward_only ON scout_lead;

DROP TABLE IF EXISTS scout_lead_stamp;
DROP TABLE IF EXISTS scout_lead;
DROP TABLE IF EXISTS lead_state;
DROP TABLE IF EXISTS content_type;

DROP FUNCTION IF EXISTS scout_lead_stamp_actor();
DROP FUNCTION IF EXISTS scout_lead_transition();
DROP FUNCTION IF EXISTS scout_pitch_digest(TEXT, INT);
DROP FUNCTION IF EXISTS scout_rfind(TEXT, TEXT);

DELETE FROM schema_version WHERE version_number = '1.5.0';

-- The role is REVOKED, never dropped. 006 creates it only if it is absent, so
-- this file cannot know whether it created the one it is looking at — and
-- dropping a role someone else made is the destructive option, while leaving a
-- login role with no privileges is inert. To remove it deliberately:
--
--     DROP ROLE scout_role;
--
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'scout_role') THEN
        EXECUTE 'REVOKE ALL ON SCHEMA public FROM scout_role';
        EXECUTE 'REVOKE ALL ON DATABASE ' || quote_ident(current_database())
                || ' FROM scout_role';
        RAISE NOTICE 'scout_role stripped of its grants and left in place';
    END IF;
END
$$;

COMMIT;
