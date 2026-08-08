-- =====================================================
-- 003 — decision_types: make the valid set real, and cardinality knowable
-- =====================================================
-- `agent_decisions.decision_type` shipped as a bare VARCHAR whose valid set
-- lived in a SQL comment: `-- 'invoke', 'route', 'classify'`. Two things went
-- wrong with that, and both were found the same way — by reading source rather
-- than by asking the database.
--
--   1. The comment is fiction. `logging_context.py` hardcodes 'invoke' in the
--      only INSERT, so 'route' and 'classify' have NEVER been written. All
--      1,395 rows are 'invoke'. Nothing detected the drift because a comment
--      cannot be queried and cannot be enforced.
--
--   2. A comment cannot say how MANY rows of a type one run produces. The
--      sysadmin agent writes one row per pass; content_agent and
--      marketer_agent.package write ~46. Designing the security agent, that
--      difference had to be discovered by reading another agent's source and
--      was initially specced wrong ("one row per pass") as a result.
--
-- `cardinality` is the column that closes (2). It turns "a run may write many
-- of these" into a fact you look up. A new session type is then a row here —
-- never a new string literal squeezed into an existing type.
--
-- Deliberately NOT seeding 'route' or 'classify'. They were never written;
-- seeding them would re-import the fiction into the structure meant to end it.
-- If a use appears, the FK forces an explicit row, which is the point.
--
-- `parent_decision_id` is untouched. It is nullable and already FK-enforced,
-- and it stays reserved for its original purpose — one agent invoking another
-- agent or a sub-agent. Findings are NOT parented under a pass; composition is
-- already expressed by `workflow_sequence_id` ("Groups all decisions in one
-- run"). Overloading parent would permanently poison "what did this agent
-- delegate", which would start returning findings.
--
-- Safe on a live table: every existing row is 'invoke', so seeding that value
-- first lets the FK validate the whole table with no backfill and no NULLs.
-- At 1,395 rows validation is instant — no NOT VALID / VALIDATE two-step
-- needed. Reversible: drop the constraint, drop the table.

BEGIN;

CREATE TABLE decision_types (
    decision_type VARCHAR(50)  PRIMARY KEY,
    description   TEXT         NOT NULL,
    -- How many rows of this type one run (one workflow_sequence_id) may write.
    -- Documentation the code can read — NOT an enforced invariant. Enforcing
    -- 'one_per_run' would want a partial unique index on
    -- (workflow_sequence_id, decision_type); deliberately deferred.
    cardinality   VARCHAR(16)  NOT NULL
                  CHECK (cardinality IN ('one_per_run', 'many_per_run')),
    added_on      DATE         NOT NULL DEFAULT CURRENT_DATE,
    retired_on    DATE                     -- set instead of deleting; keeps old rows valid
);

COMMENT ON TABLE decision_types IS
    'Valid values for agent_decisions.decision_type. Add a row to add a type — '
    'never widen an existing type to fit a new use.';

INSERT INTO decision_types (decision_type, description, cardinality, added_on) VALUES
    ('invoke',
     'A tool or agent invocation. The only type written prior to this migration; '
     'all 1,395 pre-existing rows carry it.',
     'many_per_run', '2026-04-25'),

    ('finding',
     'One distinct condition found by an audit, keyed by its stable finding id '
     '(class:target, e.g. docroot-git-exposed:studio.uzelhub.com). The id is the '
     'diff key: new/recurring/resolved is a set difference against the previous '
     'sequence, so ids are never renumbered or reworded.',
     'many_per_run', CURRENT_DATE),

    ('audit_pass',
     'Pass-level summary for an audit run — status, total cost, duration, and '
     'which charter checks were not reached. Sibling of that run''s finding rows, '
     'sharing their workflow_sequence_id; findings are NOT parented under it.',
     'one_per_run', CURRENT_DATE),

    ('refused',
     'Safety classifiers declined the request (stop_reason = refusal); category '
     'in decision_payload. Written so refusals stay countable by query — the '
     'security agent runs without a server-side fallback precisely so that a '
     'decline is visible rather than silently served by another model.',
     'one_per_run', CURRENT_DATE);

ALTER TABLE agent_decisions
    ADD CONSTRAINT agent_decisions_decision_type_fkey
    FOREIGN KEY (decision_type) REFERENCES decision_types (decision_type);

INSERT INTO schema_version (version_number, description) VALUES
    ('1.2.0',
     'decision_types lookup + FK on agent_decisions.decision_type — valid set '
     'and per-type cardinality become queryable instead of living in a comment');

COMMIT;
