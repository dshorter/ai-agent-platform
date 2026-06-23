-- =====================================================
-- AI Agent Platform — Core Schema
-- =====================================================
-- Generic spine for all agent pipelines on the platform.
-- Per-project rows are distinguished by target_site and/or
-- source_repo columns on relevant tables.
--
-- Target: PostgreSQL 15+
-- First tenant: Uzelhub commit-to-blog pipeline
-- =====================================================

-- =====================================================
-- TABLE: pipeline_runs
-- Tracks each end-to-end run of a pipeline (cron tick,
-- manual invocation, etc.). Was workflow_executions in
-- the HVAC schema.
-- =====================================================
CREATE TABLE pipeline_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_name VARCHAR(100) NOT NULL,  -- 'blog_pipeline', etc.
    target_site VARCHAR(100),             -- 'uzelhub.com', etc. (nullable for non-publishing pipelines)

    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) CHECK (status IN ('running', 'success', 'error', 'timeout')),

    duration_ms INT,
    error_message TEXT,
    error_code VARCHAR(50),

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_pipeline_runs_name ON pipeline_runs(pipeline_name);
CREATE INDEX idx_pipeline_runs_target ON pipeline_runs(target_site);
CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX idx_pipeline_runs_started ON pipeline_runs(started_at);

-- =====================================================
-- TABLE: pipeline_inputs
-- Raw inputs each pipeline ingested (commit batches,
-- webhook payloads, scheduled triggers). Generalizes
-- hvac_events.
-- =====================================================
CREATE TABLE pipeline_inputs (
    input_id SERIAL PRIMARY KEY,
    run_id UUID REFERENCES pipeline_runs(run_id),

    source_type VARCHAR(50) NOT NULL,     -- 'git_commits', 'webhook', 'scheduled'
    source_repo VARCHAR(200),             -- For git_commits: repo name
    commit_range_start VARCHAR(64),       -- For git_commits: earliest SHA in batch
    commit_range_end VARCHAR(64),         -- For git_commits: latest SHA (used for since_sha on next run)
    commit_count INT,

    event_payload JSONB,                  -- Flexible: full commit list, webhook body, etc.

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_pipeline_inputs_run ON pipeline_inputs(run_id);
CREATE INDEX idx_pipeline_inputs_source ON pipeline_inputs(source_type, source_repo);
CREATE INDEX idx_pipeline_inputs_range_end ON pipeline_inputs(source_repo, commit_range_end);
CREATE INDEX idx_pipeline_inputs_payload ON pipeline_inputs USING GIN (event_payload);

-- =====================================================
-- TABLE: agent_decisions
-- Sequence-aware log of every agent/tool invocation.
-- This is the platform's core observability spine —
-- carried forward verbatim from the HVAC schema because
-- it was designed generic from the start (LOG003 pattern).
-- =====================================================
CREATE TABLE agent_decisions (
    decision_id SERIAL PRIMARY KEY,

    run_id UUID REFERENCES pipeline_runs(run_id),
    input_id INT REFERENCES pipeline_inputs(input_id),

    agent_name VARCHAR(50) NOT NULL,       -- 'content_agent', 'marketer_agent', etc.
    decision_type VARCHAR(50) NOT NULL,    -- 'invoke', 'route', 'classify'

    decision_timestamp TIMESTAMP DEFAULT NOW(),
    processing_time_ms INT,

    llm_model VARCHAR(50),                 -- 'claude-sonnet-4-6', 'claude-haiku-4-5-20251001'
    llm_provider VARCHAR(30),              -- 'anthropic', etc.
    token_count_input INT,
    token_count_output INT,
    token_count_cache_create INT,          -- Anthropic prompt-cache write tokens
    token_count_cache_read INT,            -- Anthropic prompt-cache read tokens
    cost_usd DECIMAL(10,6),

    -- Sequence-aware logging (LOG003 pattern)
    workflow_sequence_id UUID,             -- Groups all decisions in one run
    parent_decision_id INT REFERENCES agent_decisions(decision_id),
    step_number INT,

    routing_reason TEXT,
    decision_confidence DECIMAL(3,2) CHECK (decision_confidence >= 0 AND decision_confidence <= 1),
    classification_tags TEXT[],

    action_taken VARCHAR(100),
    outcome_status VARCHAR(20) CHECK (outcome_status IN ('success', 'failed', 'pending', 'escalated')),

    decision_payload JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_decisions_run ON agent_decisions(run_id);
CREATE INDEX idx_decisions_input ON agent_decisions(input_id);
CREATE INDEX idx_decisions_agent ON agent_decisions(agent_name);
CREATE INDEX idx_decisions_timestamp ON agent_decisions(decision_timestamp);
CREATE INDEX idx_decisions_llm_model ON agent_decisions(llm_model);
CREATE INDEX idx_decisions_workflow_seq ON agent_decisions(workflow_sequence_id);
CREATE INDEX idx_decisions_parent ON agent_decisions(parent_decision_id);
CREATE INDEX idx_decisions_confidence ON agent_decisions(decision_confidence);
CREATE INDEX idx_decisions_payload ON agent_decisions USING GIN (decision_payload);

-- =====================================================
-- TABLE: posts
-- Blog posts generated by content pipelines. The
-- target_site column distinguishes per-destination
-- posts (uzelhub.com vs future targets).
-- =====================================================
CREATE TABLE posts (
    post_id SERIAL PRIMARY KEY,
    run_id UUID REFERENCES pipeline_runs(run_id),
    input_id INT REFERENCES pipeline_inputs(input_id),

    target_site VARCHAR(100) NOT NULL DEFAULT 'uzelhub.com',

    -- Content
    title TEXT NOT NULL,
    slug VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    body_html TEXT,

    -- SEO packaging (from Marketer agent)
    meta_description TEXT,
    tags TEXT[],
    series VARCHAR(100),
    primary_keyword VARCHAR(200),

    -- Cohesion graph descriptor (topics, concepts, systems, decisions)
    descriptor JSONB,

    -- Publish tracking
    ghost_post_id VARCHAR(50),
    ghost_url TEXT,
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'published', 'redirected', 'archived')),
    suggested_publish_date DATE,
    published_at TIMESTAMP,

    -- Blog Director review
    blog_director_action VARCHAR(30),      -- 'approve', 'edit', 'redirect', 'reject'
    blog_director_notes TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT posts_slug_target_unique UNIQUE (target_site, slug)
);

CREATE INDEX idx_posts_target ON posts(target_site);
CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_posts_ghost ON posts(ghost_post_id);
CREATE INDEX idx_posts_slug ON posts(slug);
CREATE INDEX idx_posts_descriptor ON posts USING GIN (descriptor);
CREATE INDEX idx_posts_tags ON posts USING GIN (tags);

-- =====================================================
-- TABLE: business_metrics
-- Pre-calculated metrics for dashboards. Generic —
-- metric_name determines semantics per pipeline.
-- =====================================================
CREATE TABLE business_metrics (
    metric_id SERIAL PRIMARY KEY,
    metric_timestamp TIMESTAMP DEFAULT NOW(),
    metric_date DATE DEFAULT CURRENT_DATE,

    metric_type VARCHAR(50) NOT NULL,      -- 'daily', 'hourly', 'event', 'cumulative'
    metric_name VARCHAR(100) NOT NULL,     -- 'posts_published', 'cost_per_post', etc.

    metric_value DECIMAL(12,4) NOT NULL,
    metric_unit VARCHAR(20),               -- 'usd', 'count', 'percentage', 'tokens'

    related_pipeline VARCHAR(100),
    related_target VARCHAR(100),
    related_run_id UUID REFERENCES pipeline_runs(run_id),

    period_start TIMESTAMP,
    period_end TIMESTAMP,

    metric_metadata JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_metrics_date ON business_metrics(metric_date);
CREATE INDEX idx_metrics_name ON business_metrics(metric_name);
CREATE INDEX idx_metrics_type ON business_metrics(metric_type);
CREATE INDEX idx_metrics_pipeline ON business_metrics(related_pipeline);

-- =====================================================
-- VIEWS
-- =====================================================

CREATE OR REPLACE VIEW v_agent_performance AS
SELECT
    agent_name,
    COUNT(*) AS total_decisions,
    AVG(processing_time_ms) AS avg_processing_ms,
    AVG(decision_confidence) AS avg_confidence,
    SUM(cost_usd) AS total_cost_usd,
    SUM(token_count_input) AS total_input_tokens,
    SUM(token_count_output) AS total_output_tokens,
    COUNT(DISTINCT DATE(decision_timestamp)) AS active_days
FROM agent_decisions
GROUP BY agent_name;

CREATE OR REPLACE VIEW v_daily_metrics AS
SELECT
    metric_date,
    metric_name,
    related_pipeline,
    related_target,
    SUM(metric_value) AS total_value,
    metric_unit,
    COUNT(*) AS metric_count
FROM business_metrics
WHERE metric_type = 'daily'
GROUP BY metric_date, metric_name, related_pipeline, related_target, metric_unit
ORDER BY metric_date DESC;

CREATE OR REPLACE VIEW v_recent_posts AS
SELECT
    p.post_id,
    p.target_site,
    p.title,
    p.slug,
    p.status,
    p.suggested_publish_date,
    p.published_at,
    p.ghost_url,
    p.created_at,
    r.pipeline_name
FROM posts p
LEFT JOIN pipeline_runs r ON p.run_id = r.run_id
ORDER BY p.created_at DESC;

-- =====================================================
-- FUNCTIONS
-- =====================================================

-- Decision tree depth (ported from HVAC schema)
CREATE OR REPLACE FUNCTION get_decision_depth(p_decision_id INT)
RETURNS INT AS $$
DECLARE
    v_depth INT := 0;
    v_parent_id INT;
BEGIN
    v_parent_id := (SELECT parent_decision_id FROM agent_decisions WHERE decision_id = p_decision_id);
    WHILE v_parent_id IS NOT NULL LOOP
        v_depth := v_depth + 1;
        v_parent_id := (SELECT parent_decision_id FROM agent_decisions WHERE decision_id = v_parent_id);
    END LOOP;
    RETURN v_depth;
END;
$$ LANGUAGE plpgsql;

-- Touch updated_at on posts
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER posts_set_updated_at
    BEFORE UPDATE ON posts
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- =====================================================
-- COMMENTS
-- =====================================================
COMMENT ON TABLE pipeline_runs IS 'One row per pipeline invocation — cron tick, manual run, etc.';
COMMENT ON TABLE pipeline_inputs IS 'Raw inputs each pipeline ingested (commit batches, webhooks)';
COMMENT ON TABLE agent_decisions IS 'Sequence-aware log of every agent/tool invocation (LOG003 pattern)';
COMMENT ON TABLE posts IS 'Generated blog drafts, tagged by target_site for multi-destination support';
COMMENT ON TABLE business_metrics IS 'Platform-level metrics for dashboards';

COMMENT ON COLUMN agent_decisions.workflow_sequence_id IS 'Groups all decisions in one run — enables decision-tree visualization';
COMMENT ON COLUMN agent_decisions.parent_decision_id IS 'Links child decisions to parent for hierarchical traces';
COMMENT ON COLUMN posts.descriptor IS 'Cohesion graph descriptor: topics, concepts, systems_mentioned, decisions_made';
COMMENT ON COLUMN posts.target_site IS 'Distinguishes per-destination posts for multi-tenant platform use';

-- =====================================================
-- SCHEMA VERSION
-- =====================================================
CREATE TABLE schema_version (
    version_id SERIAL PRIMARY KEY,
    version_number VARCHAR(20) NOT NULL,
    applied_at TIMESTAMP DEFAULT NOW(),
    description TEXT
);

INSERT INTO schema_version (version_number, description) VALUES
('1.0.0', 'Initial ai_agent_platform schema — generic spine for all pipelines, first tenant is Uzelhub blog pipeline');
