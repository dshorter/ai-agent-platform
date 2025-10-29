-- =====================================================
-- HVAC Digital Twin - PostgreSQL Database Schema
-- =====================================================
-- Generated: Tuesday, October 28, 2025 at 5:22 PM EDT
-- Purpose: Event simulation + Agent decision tracking
-- Target: PostgreSQL 15+ on Hetzner VPS  
-- Project: AI Agent Platform - HVAC Demo
-- =====================================================

-- Drop existing tables if recreating (careful in production!)
DROP TABLE IF EXISTS agent_decisions CASCADE;
DROP TABLE IF EXISTS hvac_events CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS technicians CASCADE;
DROP TABLE IF EXISTS business_metrics CASCADE;
DROP TABLE IF EXISTS workflow_executions CASCADE;

-- =====================================================
-- TABLE: customers
-- Purpose: Demo customer accounts for simulation
-- =====================================================
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    customer_type VARCHAR(20) NOT NULL CHECK (customer_type IN ('residential', 'commercial')),
    email VARCHAR(255),
    phone VARCHAR(20),
    address TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Business metrics
    lifetime_value DECIMAL(10,2) DEFAULT 0,
    maintenance_plan BOOLEAN DEFAULT FALSE,
    
    -- Demo control
    is_demo_account BOOLEAN DEFAULT TRUE,
    
    CONSTRAINT customers_email_unique UNIQUE (email)
);

CREATE INDEX idx_customers_type ON customers(customer_type);
CREATE INDEX idx_customers_maintenance ON customers(maintenance_plan);

-- =====================================================
-- TABLE: technicians
-- Purpose: Demo technician accounts for simulation
-- =====================================================
CREATE TABLE technicians (
    tech_id SERIAL PRIMARY KEY,
    tech_name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    
    -- Skills and availability
    skill_level VARCHAR(20) CHECK (skill_level IN ('junior', 'senior', 'master')),
    specialties TEXT[], -- Array of specialties: ['hvac', 'electrical', 'plumbing']
    hourly_rate DECIMAL(10,2),
    
    -- Current status
    current_status VARCHAR(20) DEFAULT 'available' 
        CHECK (current_status IN ('available', 'on_job', 'off_duty', 'break')),
    current_location POINT, -- PostgreSQL geographic point (lat, lon)
    
    -- Demo control
    is_demo_account BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT technicians_email_unique UNIQUE (email)
);

CREATE INDEX idx_technicians_status ON technicians(current_status);
CREATE INDEX idx_technicians_skill ON technicians(skill_level);

-- =====================================================
-- TABLE: hvac_events
-- Purpose: Simulated business events (customer calls, emergencies, etc)
-- =====================================================
CREATE TABLE hvac_events (
    event_id SERIAL PRIMARY KEY,
    event_timestamp TIMESTAMP DEFAULT NOW(),
    
    -- Event classification
    event_type VARCHAR(50) NOT NULL 
        CHECK (event_type IN (
            'inquiry', 
            'emergency', 
            'appointment', 
            'follow_up', 
            'maintenance',
            'billing_question',
            'complaint',
            'parts_request'
        )),
    
    -- Event details
    customer_id INT REFERENCES customers(customer_id),
    urgency INT CHECK (urgency >= 1 AND urgency <= 10), -- 1=low, 10=critical
    description TEXT,
    
    -- Business impact
    estimated_revenue DECIMAL(10,2),
    
    -- Event metadata (flexible JSON for different event types)
    event_payload JSONB,
    
    -- Simulation control
    is_manual_trigger BOOLEAN DEFAULT FALSE, -- For demo scenarios
    scenario_name VARCHAR(100), -- e.g., "2AM Emergency", "Parts Shortage"
    
    -- Processing status
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_events_type ON hvac_events(event_type);
CREATE INDEX idx_events_urgency ON hvac_events(urgency);
CREATE INDEX idx_events_timestamp ON hvac_events(event_timestamp);
CREATE INDEX idx_events_customer ON hvac_events(customer_id);
CREATE INDEX idx_events_processed ON hvac_events(processed);
CREATE INDEX idx_events_scenario ON hvac_events(scenario_name);
CREATE INDEX idx_events_payload ON hvac_events USING GIN (event_payload);

-- =====================================================
-- TABLE: workflow_executions
-- Purpose: Track n8n workflow runs (for correlation)
-- =====================================================
CREATE TABLE workflow_executions (
    execution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_name VARCHAR(100) NOT NULL, -- 'primary-agent', 'emergency-agent', etc.
    event_id INT REFERENCES hvac_events(event_id),
    
    -- Execution tracking
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) CHECK (status IN ('running', 'success', 'error', 'timeout')),
    
    -- Performance metrics
    duration_ms INT, -- Total execution time
    
    -- Error tracking
    error_message TEXT,
    error_code VARCHAR(50),
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_workflow_exec_name ON workflow_executions(workflow_name);
CREATE INDEX idx_workflow_exec_event ON workflow_executions(event_id);
CREATE INDEX idx_workflow_exec_status ON workflow_executions(status);
CREATE INDEX idx_workflow_exec_started ON workflow_executions(started_at);

-- =====================================================
-- TABLE: agent_decisions
-- Purpose: Log all agent routing and decision-making
-- Includes: Sequence-aware logging concepts (LOG003 philosophy)
-- =====================================================
CREATE TABLE agent_decisions (
    decision_id SERIAL PRIMARY KEY,
    
    -- Event correlation
    event_id INT REFERENCES hvac_events(event_id),
    workflow_execution_id UUID REFERENCES workflow_executions(execution_id),
    
    -- Agent identification
    agent_name VARCHAR(50) NOT NULL, -- 'primary', 'emergency', 'scheduling', etc.
    decision_type VARCHAR(50) NOT NULL, -- 'route', 'classify', 'escalate', 'respond'
    
    -- Timing
    decision_timestamp TIMESTAMP DEFAULT NOW(),
    processing_time_ms INT, -- How long this decision took
    
    -- LLM usage tracking
    llm_model VARCHAR(50), -- 'grok', 'gpt-4o-mini', 'claude-haiku'
    llm_provider VARCHAR(30), -- 'xai', 'openai', 'anthropic'
    token_count_input INT,
    token_count_output INT,
    cost_usd DECIMAL(10,6), -- Actual API cost
    
    -- ===================================================
    -- SEQUENCE-AWARE LOGGING (LOG003 Concept)
    -- Tracks WHY and HOW decisions flow through the system
    -- ===================================================
    
    -- Decision flow tracking
    workflow_sequence_id UUID, -- Groups all decisions in one workflow run
    parent_decision_id INT REFERENCES agent_decisions(decision_id), -- Links decisions (Primary → Specialist)
    step_number INT, -- Position in the decision sequence
    
    -- Intelligence capture
    routing_reason TEXT, -- WHY this agent/action was chosen
    decision_confidence DECIMAL(3,2) CHECK (decision_confidence >= 0 AND decision_confidence <= 1), -- 0.00-1.00
    classification_tags TEXT[], -- Array of classification tags
    
    -- Decision outcome
    action_taken VARCHAR(100), -- 'routed_to_emergency', 'sent_confirmation', etc.
    outcome_status VARCHAR(20) CHECK (outcome_status IN ('success', 'failed', 'pending', 'escalated')),
    
    -- Decision payload (flexible for different agent types)
    decision_payload JSONB, -- Stores agent-specific data
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for agent_decisions (critical for dashboard queries)
CREATE INDEX idx_decisions_event ON agent_decisions(event_id);
CREATE INDEX idx_decisions_agent ON agent_decisions(agent_name);
CREATE INDEX idx_decisions_timestamp ON agent_decisions(decision_timestamp);
CREATE INDEX idx_decisions_llm_model ON agent_decisions(llm_model);
CREATE INDEX idx_decisions_workflow_seq ON agent_decisions(workflow_sequence_id);
CREATE INDEX idx_decisions_parent ON agent_decisions(parent_decision_id);
CREATE INDEX idx_decisions_confidence ON agent_decisions(decision_confidence);
CREATE INDEX idx_decisions_payload ON agent_decisions USING GIN (decision_payload);

-- =====================================================
-- TABLE: business_metrics
-- Purpose: Pre-calculated business metrics for dashboards
-- =====================================================
CREATE TABLE business_metrics (
    metric_id SERIAL PRIMARY KEY,
    metric_timestamp TIMESTAMP DEFAULT NOW(),
    metric_date DATE DEFAULT CURRENT_DATE,
    
    -- Metric identification
    metric_type VARCHAR(50) NOT NULL, -- 'daily', 'hourly', 'event', 'cumulative'
    metric_name VARCHAR(100) NOT NULL, -- 'revenue_captured', 'time_saved', etc.
    
    -- Metric value
    metric_value DECIMAL(12,2) NOT NULL,
    metric_unit VARCHAR(20), -- 'usd', 'hours', 'count', 'percentage'
    
    -- Context
    related_event_id INT REFERENCES hvac_events(event_id),
    related_agent VARCHAR(50),
    
    -- Aggregation period
    period_start TIMESTAMP,
    period_end TIMESTAMP,
    
    -- Metadata
    calculation_method TEXT, -- How this was calculated
    metric_metadata JSONB,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_metrics_date ON business_metrics(metric_date);
CREATE INDEX idx_metrics_name ON business_metrics(metric_name);
CREATE INDEX idx_metrics_type ON business_metrics(metric_type);
CREATE INDEX idx_metrics_timestamp ON business_metrics(metric_timestamp);

-- =====================================================
-- SEED DATA: Demo Customers
-- =====================================================
INSERT INTO customers (customer_name, customer_type, email, phone, address, maintenance_plan, lifetime_value) VALUES
('John Smith', 'residential', 'customer1.smith@hvac-demo.com', '555-0101', '123 Main St, Seattle, WA', FALSE, 1200.00),
('Mary Johnson', 'residential', 'customer2.johnson@hvac-demo.com', '555-0102', '456 Oak Ave, Seattle, WA', TRUE, 3500.00),
('Acme Manufacturing', 'commercial', 'customer3.acme@hvac-demo.com', '555-0103', '789 Industrial Blvd, Seattle, WA', TRUE, 24000.00),
('Bob Wilson', 'residential', 'bob.wilson@hvac-demo.com', '555-0104', '321 Pine St, Seattle, WA', FALSE, 800.00),
('TechStart Inc', 'commercial', 'facilities@techstart-demo.com', '555-0105', '100 Innovation Way, Seattle, WA', TRUE, 18000.00);

-- =====================================================
-- SEED DATA: Demo Technicians
-- =====================================================
INSERT INTO technicians (tech_name, email, phone, skill_level, specialties, hourly_rate, current_status, current_location) VALUES
('John Martinez', 'tech.john@climatecontrolco-demo.com', '555-0201', 'senior', ARRAY['hvac', 'electrical'], 85.00, 'available', POINT(47.6062, -122.3321)),
('Sarah Chen', 'tech.sarah@climatecontrolco-demo.com', '555-0202', 'junior', ARRAY['hvac', 'maintenance'], 55.00, 'available', POINT(47.6205, -122.3493)),
('Mike Thompson', 'tech.mike@climatecontrolco-demo.com', '555-0203', 'master', ARRAY['hvac', 'electrical', 'commercial'], 110.00, 'on_job', POINT(47.5990, -122.3350)),
('Lisa Rodriguez', 'tech.lisa@climatecontrolco-demo.com', '555-0204', 'senior', ARRAY['hvac', 'residential'], 80.00, 'available', POINT(47.6097, -122.3331));

-- =====================================================
-- HELPER FUNCTIONS & VIEWS
-- =====================================================

-- View: Recent events with customer info
CREATE OR REPLACE VIEW v_recent_events AS
SELECT 
    e.event_id,
    e.event_timestamp,
    e.event_type,
    e.urgency,
    e.description,
    e.estimated_revenue,
    c.customer_name,
    c.customer_type,
    e.processed,
    e.scenario_name
FROM hvac_events e
LEFT JOIN customers c ON e.customer_id = c.customer_id
ORDER BY e.event_timestamp DESC;

-- View: Agent decision summary
CREATE OR REPLACE VIEW v_agent_performance AS
SELECT 
    agent_name,
    COUNT(*) as total_decisions,
    AVG(processing_time_ms) as avg_processing_ms,
    AVG(decision_confidence) as avg_confidence,
    SUM(cost_usd) as total_cost_usd,
    COUNT(DISTINCT DATE(decision_timestamp)) as active_days
FROM agent_decisions
GROUP BY agent_name;

-- View: Daily business metrics summary
CREATE OR REPLACE VIEW v_daily_metrics AS
SELECT 
    metric_date,
    metric_name,
    SUM(metric_value) as total_value,
    metric_unit,
    COUNT(*) as metric_count
FROM business_metrics
WHERE metric_type = 'daily'
GROUP BY metric_date, metric_name, metric_unit
ORDER BY metric_date DESC;

-- Function: Calculate decision tree depth
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

-- =====================================================
-- COMMENTS FOR DOCUMENTATION
-- =====================================================

COMMENT ON TABLE hvac_events IS 'Simulated HVAC business events for demo purposes';
COMMENT ON TABLE agent_decisions IS 'Tracks all AI agent routing decisions with sequence-aware logging (LOG003 concept)';
COMMENT ON TABLE business_metrics IS 'Pre-calculated metrics for Business Owner Dashboard';
COMMENT ON TABLE workflow_executions IS 'Tracks n8n workflow execution correlation';

COMMENT ON COLUMN agent_decisions.workflow_sequence_id IS 'Groups all decisions in one workflow run - enables decision tree visualization';
COMMENT ON COLUMN agent_decisions.parent_decision_id IS 'Links child decisions to parent (e.g., Emergency Agent → Primary Agent)';
COMMENT ON COLUMN agent_decisions.routing_reason IS 'Captures WHY this routing decision was made - critical for Technologist Dashboard';
COMMENT ON COLUMN agent_decisions.decision_confidence IS 'LLM confidence score 0.00-1.00 - helps identify uncertain decisions';

-- =====================================================
-- SCHEMA VERSION TRACKING
-- =====================================================
CREATE TABLE IF NOT EXISTS schema_version (
    version_id SERIAL PRIMARY KEY,
    version_number VARCHAR(20) NOT NULL,
    applied_at TIMESTAMP DEFAULT NOW(),
    description TEXT
);

INSERT INTO schema_version (version_number, description) VALUES
('1.0.0', 'Initial HVAC Digital Twin schema with sequence-aware logging concepts');

-- =====================================================
-- END OF SCHEMA
-- =====================================================
