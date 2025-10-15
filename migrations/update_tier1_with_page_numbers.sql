-- Update Tier 1 search function to include page numbers and fix word stemming
-- Fixes:
-- 1. Add page_number field from base table
-- 2. Use 'simple' dictionary instead of 'english' to prevent stemming ("parking" matching "park")
-- 3. Use prefix matching (:*) for partial word search

CREATE OR REPLACE FUNCTION search_provisions_tier1(
  search_query text,
  user_zone text DEFAULT NULL,
  doc_types text[] DEFAULT NULL,
  result_limit integer DEFAULT 50
)
RETURNS TABLE(
  provision_id integer,
  ref_number text,
  provision_text text,
  document_id text,
  document_type text,
  zone text,
  page_number integer,
  text_rank real,
  hierarchy_weight real,
  quant_boost real,
  zone_boost real,
  final_rank real,
  regulation_year integer,
  amendment_reference text,
  amendment_date date,
  version_status text,
  last_verified_date date,
  days_since_verified integer,
  staleness_level text
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  RETURN QUERY
  WITH ranked_provisions AS (
    SELECT
      rp.id as prov_id,
      rp.ref_number as prov_ref_number,
      rp.provision_text as prov_text,
      rp.document_id as prov_document_id,
      CASE
        WHEN rp.document_id LIKE '%SEPP%' OR rp.document_id LIKE '%State_Environmental_Planning_Policy%' THEN 'SEPP'
        WHEN rp.document_id LIKE '%Local_Environmental_Plan%' OR rp.document_id LIKE 'Inner_West_LEP%' THEN 'LEP'
        ELSE 'DCP'
      END as doc_type,
      rp.zone as prov_zone,
      COALESCE(rp_base.pdf_page, 0) as prov_page_number,
      -- Text search ranking using 'simple' dictionary (no stemming)
      ts_rank_cd(
        to_tsvector('simple', rp.provision_text || ' ' || COALESCE(rp.ref_number, '')),
        to_tsquery('simple', regexp_replace(search_query, '[^a-zA-Z0-9 ]', '', 'g') || ':*')
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
      -- Version metadata from documents table
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
    LEFT JOIN regulatory_provisions rp_base ON rp.id = rp_base.id
    LEFT JOIN documents d ON rp.document_id = d.id
    WHERE
      -- Text search condition using 'simple' dictionary (no stemming) with prefix matching
      to_tsvector('simple', rp.provision_text || ' ' || COALESCE(rp.ref_number, ''))
      @@ to_tsquery('simple', regexp_replace(search_query, '[^a-zA-Z0-9 ]', '', 'g') || ':*')
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
    prov_document_id as document_id,
    doc_type as document_type,
    prov_zone as zone,
    prov_page_number as page_number,
    prov_text_rank::REAL as text_rank,
    prov_hierarchy_weight::REAL as hierarchy_weight,
    prov_quant_boost::REAL as quant_boost,
    prov_zone_boost::REAL as zone_boost,
    (prov_text_rank * prov_hierarchy_weight * prov_quant_boost * prov_zone_boost)::REAL as final_rank,
    prov_regulation_year as regulation_year,
    prov_amendment_reference as amendment_reference,
    prov_amendment_date as amendment_date,
    prov_version_status as version_status,
    prov_last_verified_date as last_verified_date,
    prov_days_since_verified as days_since_verified,
    prov_staleness_level as staleness_level
  FROM ranked_provisions
  ORDER BY final_rank DESC
  LIMIT result_limit;
END;
$$;

-- Test queries
-- Test 1: "parking" should NOT match "Park Avenue"
SELECT COUNT(*) as parking_results
FROM search_provisions_tier1('parking', NULL, NULL, 10)
WHERE provision_text LIKE '%Park Avenue%';
-- Expected: 0

-- Test 2: "parking" should match actual parking provisions
SELECT COUNT(*) as actual_parking
FROM search_provisions_tier1('parking', NULL, NULL, 10)
WHERE provision_text ~* '\yparking\y';
-- Expected: > 0

-- Test 3: Page numbers should be populated
SELECT COUNT(*) as with_page_numbers
FROM search_provisions_tier1('parking', NULL, NULL, 10)
WHERE page_number > 0;
-- Expected: > 0
