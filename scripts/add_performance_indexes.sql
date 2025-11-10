-- NSW Planning Compliance Engine
-- Performance Optimization Indexes
-- Generated: 2025-11-10

-- ============================================================
-- Priority 1: GIN Indexes for Array Queries
-- ============================================================

-- DCP General Requirements (1,536 rows)
CREATE INDEX IF NOT EXISTS idx_dcp_gen_req_zones_gin
  ON dcp_general_requirements USING GIN (applicable_zones);

CREATE INDEX IF NOT EXISTS idx_dcp_gen_req_devtypes_gin
  ON dcp_general_requirements USING GIN (development_types);

-- DCP General Provisions (1,172 rows)
CREATE INDEX IF NOT EXISTS idx_dcp_gen_prov_zones_gin
  ON dcp_general_provisions USING GIN (applicable_zones);

CREATE INDEX IF NOT EXISTS idx_dcp_gen_prov_devtypes_gin
  ON dcp_general_provisions USING GIN (development_types);

-- ============================================================
-- Priority 2: Core Query Indexes
-- ============================================================

-- Former council filtering (used extensively in route.ts)
CREATE INDEX IF NOT EXISTS idx_dcp_gen_req_former_council
  ON dcp_general_requirements(former_council);

-- Document ID filtering (regulatory_provisions - 48k rows!)
CREATE INDEX IF NOT EXISTS idx_reg_prov_document_id
  ON regulatory_provisions(document_id);

CREATE INDEX IF NOT EXISTS idx_reg_prov_provision_type
  ON regulatory_provisions(provision_type);

-- ============================================================
-- Priority 3: Composite Indexes
-- ============================================================

-- LGA + former_council (common WHERE clause combination)
CREATE INDEX IF NOT EXISTS idx_dcp_gen_req_composite
  ON dcp_general_requirements(lga, former_council);

-- ============================================================
-- Verification Queries
-- ============================================================

-- Check index sizes
SELECT
  schemaname,
  tablename,
  indexname,
  pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND indexname LIKE 'idx_%'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Analyze tables to update statistics
ANALYZE dcp_general_requirements;
ANALYZE dcp_general_provisions;
ANALYZE regulatory_provisions;
