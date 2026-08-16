-- Diagnostic: Check Roof heritage provision text for extraction errors
-- Run this via psql or Supabase SQL editor

SELECT
    id,
    provision_number,
    pdf_page,
    v2_heritage_type,
    v2_is_actionable,
    section_header,
    LENGTH(provision_text) as text_length,
    LEFT(provision_text, 300) as text_preview,
    -- Flag suspicious patterns
    CASE
        WHEN provision_text ILIKE '%8.1.7 Heritage Items%' THEN '⚠️ Contains section header'
        WHEN provision_text ILIKE '%Heritage items are listed in Schedule 5%' THEN '⚠️ Contains intro paragraph'
        WHEN provision_text ILIKE '%1.7.1 General controls common%' THEN '⚠️ Contains generic control'
        WHEN provision_text ILIKE '%Significant internal and external features of heritage ite.%' THEN '⚠️ Truncated text'
        WHEN provision_text ILIKE '%roof%' OR provision_text ILIKE '%solar%' THEN '✅ Contains roof content'
        ELSE '❓ No roof-specific content'
    END as status
FROM regulatory_provisions
WHERE
    former_council = 'Marrickville'
    AND v2_marker = 'heritage'
    AND v2_topic = 'Roof'
ORDER BY pdf_page, id;

-- Summary
SELECT
    COUNT(*) as total_provisions,
    COUNT(CASE WHEN provision_text ILIKE '%8.1.7 Heritage Items%'
               OR provision_text ILIKE '%Heritage items are listed in Schedule 5%'
               OR provision_text ILIKE '%1.7.1 General controls common%' THEN 1 END) as suspicious_count,
    COUNT(CASE WHEN (provision_text ILIKE '%roof%' OR provision_text ILIKE '%solar%')
               AND NOT (provision_text ILIKE '%8.1.7 Heritage Items%') THEN 1 END) as looks_correct
FROM regulatory_provisions
WHERE
    former_council = 'Marrickville'
    AND v2_marker = 'heritage'
    AND v2_topic = 'Roof';
