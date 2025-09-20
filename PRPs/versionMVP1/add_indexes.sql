-- Add missing indexes for version management
CREATE INDEX IF NOT EXISTS idx_provisions_version ON regulatory_provisions(version_id, is_current);
CREATE INDEX IF NOT EXISTS idx_controls_version ON development_controls(version_id, is_current);
CREATE INDEX IF NOT EXISTS idx_standards_version ON quantitative_standards(version_id, is_current);