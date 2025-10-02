-- PRP-UI-PHASE1: Database Index Creation
-- Optimize performance for constraint queries
-- Run: psql -U postgres -d nsw_planning -f PRPs/FINALUI/scripts/create_constraint_indexes.sql

\echo 'Creating indexes for constraint queries...'

-- Index 1: Zone-based queries
-- Used by: /api/compliance/constraints (primary filter)
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_zone
ON regulatory_provisions(zone)
WHERE zone IS NOT NULL;

\echo '✓ Created index: idx_regulatory_provisions_zone'

-- Index 2: Provision type filtering
-- Used by: Constraint categorization (height/fsr/setback)
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_type
ON regulatory_provisions(provision_type)
WHERE provision_type IS NOT NULL;

\echo '✓ Created index: idx_regulatory_provisions_type'

-- Index 3: Composite zone + type
-- Used by: Combined zone and type queries (most common pattern)
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_zone_type
ON regulatory_provisions(zone, provision_type)
WHERE zone IS NOT NULL AND provision_type IS NOT NULL;

\echo '✓ Created index: idx_regulatory_provisions_zone_type'

-- Index 4: Document ID join optimization
-- Used by: Joining provisions with document metadata
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_document
ON regulatory_provisions(document_id)
WHERE document_id IS NOT NULL;

\echo '✓ Created index: idx_regulatory_provisions_document'

-- Index 5: Development permissions lookup
-- Used by: Development type permission queries
CREATE INDEX IF NOT EXISTS idx_development_permissions_zone_type
ON development_permissions(zone, development_type);

\echo '✓ Created index: idx_development_permissions_zone_type'

-- Index 6: SEPP overrides lookup
-- Used by: SEPP override detection
CREATE INDEX IF NOT EXISTS idx_sepp_overrides_clause
ON sepp_lep_overrides(affected_clause)
WHERE affected_clause IS NOT NULL;

\echo '✓ Created index: idx_sepp_overrides_clause'

-- Analyze tables to update statistics
\echo 'Analyzing tables for query optimization...'

ANALYZE regulatory_provisions;
ANALYZE development_permissions;
ANALYZE sepp_lep_overrides;
ANALYZE documents;

\echo '✓ Table statistics updated'

-- Show index sizes
\echo ''
\echo 'Index sizes:'
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as size
FROM pg_indexes
WHERE schemaname = 'public'
AND tablename IN ('regulatory_provisions', 'development_permissions', 'sepp_lep_overrides')
ORDER BY tablename, indexname;

\echo ''
\echo '✓ All indexes created successfully'
\echo 'Run verify_phase1.py to test performance improvements'