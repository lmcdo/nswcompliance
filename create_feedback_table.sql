-- Create user feedback table for professional users
-- Run this: psql -U postgres -d nsw_planning -f create_feedback_table.sql

CREATE TABLE IF NOT EXISTS user_feedback (
  id SERIAL PRIMARY KEY,

  -- Feedback content
  feedback_type VARCHAR(50) NOT NULL CHECK (
    feedback_type IN (
      'data_accuracy',
      'missing_info',
      'feature_request',
      'ui_ux',
      'bug_report',
      'general'
    )
  ),
  feedback_text TEXT NOT NULL,
  email VARCHAR(255),

  -- Page context
  page VARCHAR(500),
  url TEXT,

  -- Property context
  property_address TEXT,

  -- Provision context
  provision_id INTEGER,
  provision_title TEXT,
  provision_source TEXT,

  -- Technical context
  browser_info TEXT,
  screen_resolution VARCHAR(50),

  -- Full context JSON (for debugging and detailed analysis)
  context_data JSONB,

  -- Status tracking (for internal use)
  status VARCHAR(20) DEFAULT 'new' CHECK (
    status IN ('new', 'reviewed', 'in_progress', 'resolved', 'archived')
  ),
  internal_notes TEXT,
  assigned_to VARCHAR(255),

  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  resolved_at TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_feedback_type ON user_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_feedback_status ON user_feedback(status);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON user_feedback(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_property ON user_feedback(property_address);

-- Full-text search on feedback text
CREATE INDEX IF NOT EXISTS idx_feedback_text_search
  ON user_feedback
  USING gin(to_tsvector('english', feedback_text));

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_feedback_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_feedback_timestamp
  BEFORE UPDATE ON user_feedback
  FOR EACH ROW
  EXECUTE FUNCTION update_feedback_timestamp();

-- Table and column comments
COMMENT ON TABLE user_feedback IS 'Stores user feedback from professional users (certifiers, town planners)';
COMMENT ON COLUMN user_feedback.feedback_type IS 'Category of feedback for filtering and prioritization';
COMMENT ON COLUMN user_feedback.context_data IS 'Full JSON context for debugging and detailed analysis';
COMMENT ON COLUMN user_feedback.status IS 'Internal status for tracking feedback resolution';

-- Grant permissions (if using specific user)
-- GRANT SELECT, INSERT ON user_feedback TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE user_feedback_id_seq TO your_app_user;

-- Success message
DO $$
BEGIN
  RAISE NOTICE 'User feedback table created successfully!';
  RAISE NOTICE 'Table: user_feedback';
  RAISE NOTICE 'Indexes: 4 created';
  RAISE NOTICE 'Ready to accept feedback from professional users.';
END $$;
