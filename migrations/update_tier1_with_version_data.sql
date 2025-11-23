-- ============================================================
-- UPDATE TIER1 RANKING FUNCTION WITH VERSION METADATA
-- Adds version tracking fields to search_provisions_tier1() output
-- For certifier legal compliance and staleness warnings
-- ============================================================

BEGIN;

-- Drop existing function
DROP FUNCTION IF EXISTS search_provisions_tier1(TEXT, TEXT, TEXT[], INTEGER);

-- Recreate with version metadata fields
CREATE OR REPLACE FUNCTION search_provisions_tier1(
  search_query TEXT,
  user_zone TEXT DEFAULT NULL,
  doc_types TEXT[] DEFAULT NULL,
  result_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
  provision_id INTEGER,
  ref_number TEXT,
  provision_text TEXT,
  document_type TEXT,
  zone TEXT,
  text_rank REAL,
  hierarchy_weight REAL,
  quant_boost REAL,
  zone_boost REAL,
  final_rank REAL,
  -- NEW: Version metadata fields
  regulation_year INTEGER,
  amendment_reference TEXT,
  amendment_date DATE,
  version_status TEXT,
  last_verified_date DATE,
  days_since_verified INTEGER,
  staleness_level TEXT
)
AS $$
BEGIN
  RETURN QUERY
  WITH ranked_provisions AS (
    SELECT
      rp.id as prov_id,
      rp.ref_number as prov_ref_number,
      rp.provision_text as prov_text,
      CASE
        WHEN rp.document_id LIKE '%SEPP%' OR rp.document_id LIKE '%State Environmental Planning Policy%' THEN 'SEPP'
        WHEN rp.document_id LIKE '%LEP%' OR rp.document_id LIKE '%Environmental_Plan%' THEN 'LEP'
        ELSE 'DCP'
      END as doc_type,
      rp.zone as prov_zone,
      -- Text search ranking
      ts_rank_cd(
        to_tsvector('english', rp.provision_text || ' ' || COALESCE(rp.ref_number, '')),
        plainto_tsquery('english', search_query)
      ) as prov_text_rank,
      -- Hierarchy weight (SEPP=10, LEP=5, DCP=1)
      CASE
        WHEN rp.document_id LIKE '%SEPP%' THEN 10.0
        WHEN rp.document_id LIKE '%LEP%' THEN 5.0
        ELSE 1.0
      END as prov_hierarchy_weight,
      -- Quantitative standards boost (detect numbers in text)
      CASE
        WHEN rp.provision_text ~ '\d+\.?\d*\s*(m|metre|meter|storey|floor|:1|%)' THEN 2.0
        ELSE 1.0
      END as prov_quant_boost,
      -- Zone matching boost
      CASE
        WHEN user_zone IS NULL THEN 1.0
        WHEN rp.zone = user_zone THEN 5.0
        WHEN rp.zone IS NULL THEN 1.0
        ELSE 0.3
      END as prov_zone_boost,
      -- NEW: Version metadata from documents table
      d.regulation_year as prov_regulation_year,
      d.amendment_reference as prov_amendment_reference,
      d.amendment_date as prov_amendment_date,
      d.version_status as prov_version_status,
      d.last_verified_date as prov_last_verified_date,
      CURRENT_DATE - d.last_verified_date as prov_days_since_verified,
      CASE
        WHEN CURRENT_DATE - d.last_verified_date <= 30 THEN 'current'
        WHEN CURRENT_DATE - d.last_verified_date <= 60 THEN 'caution'
        ELSE 'stale'
      END as prov_staleness_level
    FROM regulatory_provisions_canonical rp
    LEFT JOIN documents d ON rp.document_id = d.id
    WHERE
      -- Text search condition
      to_tsvector('english', rp.provision_text || ' ' || COALESCE(rp.ref_number, ''))
      @@ plainto_tsquery('english', search_query)
      -- Document type filter (if provided)
      AND (
        doc_types IS NULL
        OR (
          (rp.document_id LIKE '%SEPP%' AND 'SEPP' = ANY(doc_types))
          OR (rp.document_id LIKE '%LEP%' AND 'LEP' = ANY(doc_types))
          OR (rp.document_id NOT LIKE '%SEPP%' AND rp.document_id NOT LIKE '%LEP%' AND 'DCP' = ANY(doc_types))
        )
      )
  )
  SELECT
    prov_id as provision_id,
    prov_ref_number as ref_number,
    prov_text as provision_text,
    doc_type as document_type,
    prov_zone as zone,
    prov_text_rank::REAL as text_rank,
    prov_hierarchy_weight::REAL as hierarchy_weight,
    prov_quant_boost::REAL as quant_boost,
    prov_zone_boost::REAL as zone_boost,
    (prov_text_rank * prov_hierarchy_weight * prov_quant_boost * prov_zone_boost)::REAL as final_rank,
    -- Version metadata
    prov_regulation_year as regulation_year,
    prov_amendment_reference as amendment_reference,
    prov_amendment_date as amendment_date,
    prov_version_status as version_status,
    prov_last_verified_date as last_verified_date,
    prov_days_since_verified as days_since_verified,
    prov_staleness_level as staleness_level
  FROM ranked_provisions
  ORDER BY (prov_text_rank * prov_hierarchy_weight * prov_quant_boost * prov_zone_boost) DESC
  LIMIT result_limit;
END;
$$ LANGUAGE plpgsql STABLE;

COMMIT;

-- ============================================================
-- VERIFICATION QUERY
-- Test that version metadata is returned
-- ============================================================
SELECT
  provision_id,
  ref_number,
  document_type,
  regulation_year,
  amendment_reference,
  days_since_verified,
  staleness_level,
  final_rank
FROM search_provisions_tier1('setback', 'R1', NULL, 5);
