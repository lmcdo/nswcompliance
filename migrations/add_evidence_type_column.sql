-- Add evidence_type column to dcp_general_requirements
-- Based on USEFUL_DCP_DATA_PERSPECTIVES.md and LLM_EXTRACTION_REALISTIC_ASSESSMENT.md

ALTER TABLE dcp_general_requirements
ADD COLUMN IF NOT EXISTS evidence_type TEXT;

COMMENT ON COLUMN dcp_general_requirements.evidence_type IS
'Classification of evidence required for compliance:
- measurable: Objective measurements (6m setback, 1 parking space)
- calculable: Requires calculation (FSR, site coverage %)
- assessable: Subjective merit assessment (character compatibility)
- reportable: Requires specialist report (acoustic, BASIX)';

-- Add index for filtering
CREATE INDEX IF NOT EXISTS idx_dcp_general_requirements_evidence_type
ON dcp_general_requirements(evidence_type);

-- Add to precinct requirements table too
ALTER TABLE dcp_precinct_requirements
ADD COLUMN IF NOT EXISTS evidence_type TEXT;

COMMENT ON COLUMN dcp_precinct_requirements.evidence_type IS
'Classification of evidence required for compliance:
- measurable: Objective measurements (6m setback, 1 parking space)
- calculable: Requires calculation (FSR, site coverage %)
- assessable: Subjective merit assessment (character compatibility)
- reportable: Requires specialist report (acoustic, BASIX)';

CREATE INDEX IF NOT EXISTS idx_dcp_precinct_requirements_evidence_type
ON dcp_precinct_requirements(evidence_type);
