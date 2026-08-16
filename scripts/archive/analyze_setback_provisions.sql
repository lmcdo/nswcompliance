-- Setback Provisions Analysis Script
-- Purpose: Analyze setback data across 3 councils (Marrickville, Ashfield, Leichhardt)
-- to understand provision types, values, and presentation requirements

-- ============================================================================
-- SECTION 1: Overview - Count setback provisions by council
-- ============================================================================

SELECT
    '=== SETBACK PROVISIONS OVERVIEW ===' as section;

SELECT
    former_council,
    COUNT(*) as total_setback_provisions,
    COUNT(CASE WHEN value_numeric IS NOT NULL THEN 1 END) as with_numeric_value,
    COUNT(CASE WHEN value_numeric IS NULL THEN 1 END) as without_numeric_value,
    ROUND(100.0 * COUNT(CASE WHEN value_numeric IS NOT NULL THEN 1 END) / COUNT(*), 1) as pct_numeric
FROM dcp_general_requirements
WHERE category ILIKE '%setback%'
GROUP BY former_council
ORDER BY former_council;

-- ============================================================================
-- SECTION 2: MARRICKVILLE - All setback provisions
-- ============================================================================

SELECT
    '=== MARRICKVILLE SETBACK PROVISIONS ===' as section;

-- 2a. Numerical setback provisions (calculable)
SELECT
    'MARRICKVILLE - NUMERICAL VALUES' as council_type,
    category,
    subcategory,
    requirement_text,
    value_numeric,
    value_min,
    value_max,
    unit,
    has_conditionals,
    conditional_text,
    confidence,
    pdf_page
FROM dcp_general_requirements
WHERE former_council = 'Marrickville'
AND category ILIKE '%setback%'
AND value_numeric IS NOT NULL
ORDER BY category, value_numeric;

-- 2b. Non-numerical setback provisions (interpretive)
SELECT
    'MARRICKVILLE - INTERPRETIVE (NO NUMBER)' as council_type,
    category,
    subcategory,
    LEFT(requirement_text, 300) as requirement_text_preview,
    has_conditionals,
    conditional_text,
    confidence,
    pdf_page
FROM dcp_general_requirements
WHERE former_council = 'Marrickville'
AND category ILIKE '%setback%'
AND value_numeric IS NULL
ORDER BY category
LIMIT 20;

-- ============================================================================
-- SECTION 3: ASHFIELD - All setback provisions
-- ============================================================================

SELECT
    '=== ASHFIELD SETBACK PROVISIONS ===' as section;

-- 3a. Numerical setback provisions
SELECT
    'ASHFIELD - NUMERICAL VALUES' as council_type,
    category,
    subcategory,
    requirement_text,
    value_numeric,
    value_min,
    value_max,
    unit,
    has_conditionals,
    conditional_text,
    confidence,
    pdf_page
FROM dcp_general_requirements
WHERE former_council = 'Ashfield'
AND category ILIKE '%setback%'
AND value_numeric IS NOT NULL
ORDER BY category, value_numeric;

-- 3b. Non-numerical setback provisions
SELECT
    'ASHFIELD - INTERPRETIVE (NO NUMBER)' as council_type,
    category,
    subcategory,
    LEFT(requirement_text, 300) as requirement_text_preview,
    has_conditionals,
    conditional_text,
    confidence,
    pdf_page
FROM dcp_general_requirements
WHERE former_council = 'Ashfield'
AND category ILIKE '%setback%'
AND value_numeric IS NULL
ORDER BY category
LIMIT 20;

-- ============================================================================
-- SECTION 4: LEICHHARDT - All setback provisions
-- ============================================================================

SELECT
    '=== LEICHHARDT SETBACK PROVISIONS ===' as section;

-- 4a. Numerical setback provisions
SELECT
    'LEICHHARDT - NUMERICAL VALUES' as council_type,
    category,
    subcategory,
    requirement_text,
    value_numeric,
    value_min,
    value_max,
    unit,
    has_conditionals,
    conditional_text,
    confidence,
    pdf_page
FROM dcp_general_requirements
WHERE former_council = 'Leichhardt'
AND category ILIKE '%setback%'
AND value_numeric IS NOT NULL
ORDER BY category, value_numeric;

-- 4b. Non-numerical setback provisions
SELECT
    'LEICHHARDT - INTERPRETIVE (NO NUMBER)' as council_type,
    category,
    subcategory,
    LEFT(requirement_text, 300) as requirement_text_preview,
    has_conditionals,
    conditional_text,
    confidence,
    pdf_page
FROM dcp_general_requirements
WHERE former_council = 'Leichhardt'
AND category ILIKE '%setback%'
AND value_numeric IS NULL
ORDER BY category
LIMIT 20;

-- ============================================================================
-- SECTION 5: Analyze provision patterns
-- ============================================================================

SELECT
    '=== PROVISION PATTERN ANALYSIS ===' as section;

-- 5a. Setback categories breakdown
SELECT
    former_council,
    category,
    COUNT(*) as count
FROM dcp_general_requirements
WHERE category ILIKE '%setback%'
GROUP BY former_council, category
ORDER BY former_council, count DESC;

-- 5b. Provisions with formulas (contain %, x, times, or)
SELECT
    'FORMULA-BASED PROVISIONS' as type,
    former_council,
    category,
    LEFT(requirement_text, 200) as requirement_preview,
    value_numeric,
    unit
FROM dcp_general_requirements
WHERE category ILIKE '%setback%'
AND (
    requirement_text ILIKE '%% of%'
    OR requirement_text ILIKE '%times%'
    OR requirement_text ILIKE '%x height%'
    OR requirement_text ILIKE '%or greater%'
    OR requirement_text ILIKE '%whichever%'
)
ORDER BY former_council
LIMIT 30;

-- 5c. Streetscape/character provisions (interpretive)
SELECT
    'STREETSCAPE/CHARACTER PROVISIONS' as type,
    former_council,
    category,
    LEFT(requirement_text, 200) as requirement_preview
FROM dcp_general_requirements
WHERE category ILIKE '%setback%'
AND (
    requirement_text ILIKE '%streetscape%'
    OR requirement_text ILIKE '%character%'
    OR requirement_text ILIKE '%consistent with%'
    OR requirement_text ILIKE '%in keeping%'
    OR requirement_text ILIKE '%established%'
)
ORDER BY former_council
LIMIT 20;

-- ============================================================================
-- SECTION 6: Zone-specific setbacks (if zone data exists)
-- ============================================================================

SELECT
    '=== ZONE-SPECIFIC SETBACKS ===' as section;

-- Check if applicable_zones has data
SELECT
    former_council,
    category,
    applicable_zones,
    LEFT(requirement_text, 150) as requirement_preview,
    value_numeric,
    unit
FROM dcp_general_requirements
WHERE category ILIKE '%setback%'
AND applicable_zones IS NOT NULL
AND array_length(applicable_zones, 1) > 0
ORDER BY former_council, applicable_zones
LIMIT 30;

-- ============================================================================
-- SECTION 7: Precinct-specific setbacks
-- ============================================================================

SELECT
    '=== PRECINCT-SPECIFIC SETBACKS ===' as section;

SELECT
    former_council,
    precinct_name,
    category,
    LEFT(requirement_text, 200) as requirement_preview,
    value_numeric,
    unit,
    confidence
FROM dcp_precinct_requirements
WHERE category ILIKE '%setback%'
ORDER BY former_council, precinct_name
LIMIT 40;

-- ============================================================================
-- SECTION 8: Summary statistics
-- ============================================================================

SELECT
    '=== SUMMARY STATISTICS ===' as section;

SELECT
    former_council,
    COUNT(*) FILTER (WHERE category = 'setbacks') as general_setbacks,
    COUNT(*) FILTER (WHERE category = 'setback_front') as front_setbacks,
    COUNT(*) FILTER (WHERE category = 'setback_side') as side_setbacks,
    COUNT(*) FILTER (WHERE category = 'setback_rear') as rear_setbacks,
    COUNT(*) FILTER (WHERE value_numeric IS NOT NULL) as calculable,
    COUNT(*) FILTER (WHERE requirement_text ILIKE '%streetscape%' OR requirement_text ILIKE '%character%') as interpretive,
    COUNT(*) FILTER (WHERE requirement_text ILIKE '%% of%' OR requirement_text ILIKE '%times%') as formula_based
FROM dcp_general_requirements
WHERE category ILIKE '%setback%'
GROUP BY former_council
ORDER BY former_council;
