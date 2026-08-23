-- Migration: Add v2_display_priority for UX optimization
-- Date: 2026-01-27
-- Purpose: Rank provisions for progressive disclosure UI
--          Critical provisions shown first, guidelines collapsed by default

-- Add column
ALTER TABLE regulatory_provisions
ADD COLUMN IF NOT EXISTS v2_display_priority VARCHAR(20);

-- Populate based on existing metadata
UPDATE regulatory_provisions
SET v2_display_priority = CASE
  -- Critical: Quantitative controls (CDC-eligible, has numeric values)
  WHEN v2_provision_type = 'control'
   AND v2_has_numeric_value = true
   THEN 'critical'

  -- Important: Controls without numeric values (standard compliance)
  WHEN v2_provision_type = 'control'
   AND (v2_has_numeric_value = false OR v2_has_numeric_value IS NULL)
   THEN 'important'

  -- Guideline: Objectives, performance criteria (design guidance)
  WHEN v2_provision_type IN ('objective', 'performance_criteria')
   THEN 'guideline'

  -- Contextual: Notes, references (already filtered by v2_is_actionable)
  WHEN v2_provision_type IN ('note', 'reference')
   THEN 'contextual'

  -- Default: Important for anything else
  ELSE 'important'
END
WHERE v2_is_actionable = true;

-- Create index for fast filtering
CREATE INDEX IF NOT EXISTS idx_provisions_display_priority
ON regulatory_provisions(v2_display_priority)
WHERE v2_is_actionable = true;

-- Verification query
SELECT
  v2_display_priority,
  v2_provision_type,
  v2_has_numeric_value,
  COUNT(*) as count
FROM regulatory_provisions
WHERE v2_is_actionable = true
GROUP BY v2_display_priority, v2_provision_type, v2_has_numeric_value
ORDER BY
  CASE v2_display_priority
    WHEN 'critical' THEN 1
    WHEN 'important' THEN 2
    WHEN 'guideline' THEN 3
    WHEN 'contextual' THEN 4
    ELSE 5
  END,
  count DESC;
