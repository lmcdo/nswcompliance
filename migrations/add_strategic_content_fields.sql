-- Add strategic/descriptive content fields to dcp_general_requirements
-- These fields capture the WHY, WHEN FLEXIBLE, and heritage context

ALTER TABLE dcp_general_requirements
ADD COLUMN IF NOT EXISTS objective TEXT,  -- WHY this requirement exists
ADD COLUMN IF NOT EXISTS performance_criteria TEXT,  -- WHAT outcome to achieve
ADD COLUMN IF NOT EXISTS heritage_context TEXT,  -- Heritage significance if applicable
ADD COLUMN IF NOT EXISTS allows_alternative_solutions BOOLEAN DEFAULT false,  -- Can this be varied?
ADD COLUMN IF NOT EXISTS alternative_solutions_criteria TEXT;  -- What to demonstrate for variation

COMMENT ON COLUMN dcp_general_requirements.objective IS 'The planning objective - explains WHY this requirement exists (e.g., "To maintain streetscape character")';
COMMENT ON COLUMN dcp_general_requirements.performance_criteria IS 'Performance-based outcome to achieve - enables alternative solutions if outcome met';
COMMENT ON COLUMN dcp_general_requirements.heritage_context IS 'Heritage Conservation Area significance statement if applicable';
COMMENT ON COLUMN dcp_general_requirements.allows_alternative_solutions IS 'Whether alternative solutions are explicitly mentioned as acceptable';
COMMENT ON COLUMN dcp_general_requirements.alternative_solutions_criteria IS 'Criteria for alternative solutions to be considered acceptable';
