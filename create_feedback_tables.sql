-- Create feedback tables for professional user feedback collection
-- Run this in your PostgreSQL database to set up the feedback system

-- Main user feedback table
CREATE TABLE IF NOT EXISTS user_feedback (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL, -- 'address_issue', 'missing_data', 'incorrect_calculation', 'general'
    property_address TEXT NOT NULL,
    section VARCHAR(100), -- 'dcp_general', 'precinct_requirements', 'setbacks', etc.
    description TEXT NOT NULL,
    user_type VARCHAR(50) NOT NULL, -- 'certifier', 'planner', 'developer', 'architect', 'other'
    severity VARCHAR(10) NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
    contact_email VARCHAR(255),
    context_data JSONB, -- Additional context for debugging
    user_agent TEXT,
    ip_address INET,
    created_at TIMESTAMP DEFAULT NOW(),
    resolved BOOLEAN DEFAULT FALSE,
    resolution_notes TEXT,
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100)
);

-- Requirement-specific feedback table
CREATE TABLE IF NOT EXISTS requirement_feedback (
    id SERIAL PRIMARY KEY,
    requirement_id TEXT NOT NULL,
    property_address TEXT NOT NULL,
    feedback_type VARCHAR(20) NOT NULL CHECK (feedback_type IN ('correct', 'incorrect', 'missing_context', 'outdated')),
    description TEXT NOT NULL,
    user_type VARCHAR(50) NOT NULL,
    urgency VARCHAR(10) NOT NULL CHECK (urgency IN ('low', 'medium', 'high')),
    requirement_context JSONB, -- Details about the requirement
    user_agent TEXT,
    ip_address INET,
    created_at TIMESTAMP DEFAULT NOW(),
    reviewed BOOLEAN DEFAULT FALSE,
    review_notes TEXT
);

-- Simple vote tracking for requirements
CREATE TABLE IF NOT EXISTS requirement_votes (
    id SERIAL PRIMARY KEY,
    requirement_id TEXT NOT NULL,
    property_address TEXT NOT NULL,
    vote_type VARCHAR(10) NOT NULL CHECK (vote_type IN ('up', 'down')),
    user_agent TEXT,
    ip_address INET,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(requirement_id, property_address, ip_address) -- One vote per property per IP
);

-- Metrics aggregation for requirements
CREATE TABLE IF NOT EXISTS requirement_metrics (
    requirement_id TEXT PRIMARY KEY,
    correct_votes INTEGER DEFAULT 0,
    incorrect_votes INTEGER DEFAULT 0,
    total_votes INTEGER DEFAULT 0,
    accuracy_score DECIMAL(5,2), -- Percentage of correct votes
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Review queue for requirements with multiple issues
CREATE TABLE IF NOT EXISTS requirement_review_queue (
    id SERIAL PRIMARY KEY,
    requirement_id TEXT NOT NULL,
    issue_count INTEGER NOT NULL,
    avg_urgency DECIMAL(3,1) NOT NULL,
    flagged_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'resolved', 'dismissed')),
    assigned_to VARCHAR(100),
    reviewed_at TIMESTAMP,
    review_notes TEXT,
    UNIQUE(requirement_id)
);

-- Add vote tracking to existing requirements table if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'dcp_general_requirements'
        AND column_name = 'up_votes'
    ) THEN
        ALTER TABLE dcp_general_requirements
        ADD COLUMN up_votes INTEGER DEFAULT 0,
        ADD COLUMN down_votes INTEGER DEFAULT 0,
        ADD COLUMN vote_score DECIMAL(5,2) DEFAULT 0,
        ADD COLUMN last_vote_updated TIMESTAMP;
    END IF;
END $$;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_feedback_type ON user_feedback(type);
CREATE INDEX IF NOT EXISTS idx_user_feedback_section ON user_feedback(section);
CREATE INDEX IF NOT EXISTS idx_user_feedback_severity ON user_feedback(severity);
CREATE INDEX IF NOT EXISTS idx_user_feedback_created ON user_feedback(created_at);
CREATE INDEX IF NOT EXISTS idx_user_feedback_property ON user_feedback(property_address);
CREATE INDEX IF NOT EXISTS idx_user_feedback_resolved ON user_feedback(resolved);

CREATE INDEX IF NOT EXISTS idx_requirement_feedback_id ON requirement_feedback(requirement_id);
CREATE INDEX IF NOT EXISTS idx_requirement_feedback_type ON requirement_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_requirement_feedback_created ON requirement_feedback(created_at);

CREATE INDEX IF NOT EXISTS idx_requirement_votes_id ON requirement_votes(requirement_id);
CREATE INDEX IF NOT EXISTS idx_requirement_votes_created ON requirement_votes(created_at);

CREATE INDEX IF NOT EXISTS idx_requirement_review_queue_status ON requirement_review_queue(status);
CREATE INDEX IF NOT EXISTS idx_requirement_review_queue_flagged ON requirement_review_queue(flagged_at);

-- Create view for feedback analytics
CREATE OR REPLACE VIEW feedback_analytics AS
SELECT
    DATE_TRUNC('day', created_at) as feedback_date,
    user_type,
    type,
    severity,
    COUNT(*) as feedback_count,
    AVG(CASE WHEN severity = 'high' THEN 3 WHEN severity = 'medium' THEN 2 ELSE 1 END) as avg_severity_score
FROM user_feedback
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', created_at), user_type, type, severity
ORDER BY feedback_date DESC;

-- Create view for requirement performance
CREATE OR REPLACE VIEW requirement_performance AS
SELECT
    r.id as requirement_id,
    r.category,
    r.section_title,
    r.former_council as council,
    COALESCE(m.correct_votes, 0) as correct_votes,
    COALESCE(m.incorrect_votes, 0) as incorrect_votes,
    COALESCE(m.total_votes, 0) as total_votes,
    COALESCE(m.accuracy_score, 0) as accuracy_score,
    COALESCE(v.up_votes, 0) as up_votes,
    COALESCE(v.down_votes, 0) as down_votes,
    COALESCE(v.vote_score, 0) as vote_score,
    q.issue_count,
    q.avg_urgency,
    q.status as review_status
FROM dcp_general_requirements r
LEFT JOIN requirement_metrics m ON r.id::text = m.requirement_id
LEFT JOIN LATERAL (
    SELECT
        requirement_id,
        SUM(CASE WHEN vote_type = 'up' THEN 1 ELSE 0 END) as up_votes,
        SUM(CASE WHEN vote_type = 'down' THEN 1 ELSE 0 END) as down_votes,
        CASE
            WHEN (SUM(CASE WHEN vote_type = 'up' THEN 1 ELSE 0 END) +
                 SUM(CASE WHEN vote_type = 'down' THEN 1 ELSE 0 END)) = 0 THEN 0
            ELSE ROUND((SUM(CASE WHEN vote_type = 'up' THEN 1 ELSE 0 END)::numeric /
                       (SUM(CASE WHEN vote_type = 'up' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN vote_type = 'down' THEN 1 ELSE 0 END))) * 100, 1)
        END as vote_score
    FROM requirement_votes
    WHERE created_at > NOW() - INTERVAL '30 days'
    AND requirement_id = r.id::text
    GROUP BY requirement_id
) v ON true
LEFT JOIN requirement_review_queue q ON r.id::text = q.requirement_id
WHERE r.id IS NOT NULL;

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE ON user_feedback TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE ON requirement_feedback TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE ON requirement_votes TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE ON requirement_metrics TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE ON requirement_review_queue TO your_app_user;

-- Grant permissions on sequences
-- GRANT USAGE, SELECT ON SEQUENCE user_feedback_id_seq TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE requirement_feedback_id_seq TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE requirement_votes_id_seq TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE requirement_review_queue_id_seq TO your_app_user;

-- Grant select on views
-- GRANT SELECT ON feedback_analytics TO your_app_user;
-- GRANT SELECT ON requirement_performance TO your_app_user;

COMMENT ON TABLE user_feedback IS 'Main feedback collection from professional users';
COMMENT ON TABLE requirement_feedback IS 'Specific feedback about individual requirements';
COMMENT ON TABLE requirement_votes IS 'Simple up/down votes for requirements';
COMMENT ON TABLE requirement_metrics IS 'Aggregated metrics for requirement accuracy';
COMMENT ON TABLE requirement_review_queue IS 'Requirements that need content review due to multiple issues';

COMMENT ON COLUMN user_feedback.type IS 'Type of feedback: address_issue, missing_data, incorrect_calculation, general';
COMMENT ON COLUMN user_feedback.severity IS 'Impact severity: low, medium, high';
COMMENT ON COLUMN user_feedback.user_type IS 'Professional role: certifier, planner, developer, architect, other';
COMMENT ON COLUMN requirement_feedback.feedback_type IS 'Specific issue type: correct, incorrect, missing_context, outdated';
COMMENT ON COLUMN requirement_feedback.urgency IS 'How urgent this issue is: low, medium, high';