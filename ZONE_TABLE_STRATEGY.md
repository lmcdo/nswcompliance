# Zone Setback Tables Strategy: Combine vs Separate

## Current State
- **zone_setback_rules**: 6 rules, 0.95 confidence (Ashfield/Leichhardt R2 only)
- **zone_setback_rules_comprehensive**: 42 rules, 0.75-0.95 confidence (all councils, 7 zones)

## Option 1: COMBINE INTO SINGLE TABLE (Recommended)

### Implementation
```sql
-- Merge tables with confidence scoring
INSERT INTO zone_setback_rules (
 rule_id, zone, council, boundary_type, base_value, unit,
 operator, authority_type, precedence_level, conditions,
 source_document, source_clause, source_file, confidence
)
SELECT * FROM zone_setback_rules_comprehensive
ON CONFLICT (rule_id) DO UPDATE SET
 confidence = GREATEST(EXCLUDED.confidence, zone_setback_rules.confidence);
```

### Pros
- **Single source of truth** - Frontend queries one table
- **Simpler API logic** - No conditional table selection
- **Better performance** - One index, one query
- **Easier maintenance** - Updates in one place
- **Natural hierarchy** - Confidence scores handle quality differences

### Cons
- **Mixed quality data** - High and medium confidence together
- **No rollback option** - Can't easily revert to high-confidence only
- **Potential conflicts** - Same zone/boundary might have multiple rules

## Option 2: KEEP SEPARATE, QUERY BOTH

### Implementation
```typescript
// API queries both tables with fallback
async function getSetbackRules(zone: string, council: string) {
 // Try high-confidence first
 let rules = await db.query('SELECT * FROM zone_setback_rules WHERE zone = $1 AND council = $2', [zone, council]);
 
 // Fallback to comprehensive if no results
 if (rules.length === 0) {
 rules = await db.query('SELECT * FROM zone_setback_rules_comprehensive WHERE zone = $1 AND council = $2', [zone, council]);
 }
 
 return rules;
}
```

### Pros
- **Quality isolation** - Can choose confidence level
- **A/B testing possible** - Compare results between tables
- **Rollback capability** - Can revert to high-confidence only

### Cons
- **Complex API logic** - Conditional queries needed
- **Performance overhead** - Potentially two queries per request
- **Maintenance burden** - Two tables to update
- **User confusion** - Which table is authoritative?

## Option 3: CREATE UNIFIED VIEW (Best of Both)

### Implementation
```sql
-- Create materialized view combining both with quality tiers
CREATE MATERIALIZED VIEW zone_setback_rules_unified AS
SELECT 
 rule_id,
 zone,
 council,
 boundary_type,
 base_value,
 unit,
 operator,
 authority_type,
 precedence_level,
 conditions,
 source_document,
 source_clause,
 confidence,
 CASE 
 WHEN confidence >= 0.95 THEN 'verified'
 WHEN confidence >= 0.85 THEN 'high'
 WHEN confidence >= 0.75 THEN 'medium'
 ELSE 'low'
 END as quality_tier,
 CASE
 WHEN source_file LIKE '%inner-west-compliance-rules%' THEN 1
 WHEN source_file LIKE '%langextract_verified%' THEN 2
 ELSE 3
 END as source_priority
FROM (
 SELECT * FROM zone_setback_rules
 UNION ALL
 SELECT * FROM zone_setback_rules_comprehensive
) combined
WHERE NOT EXISTS (
 -- Remove duplicates, keeping highest confidence
 SELECT 1 FROM zone_setback_rules_comprehensive c2
 WHERE c2.zone = combined.zone 
 AND c2.council = combined.council
 AND c2.boundary_type = combined.boundary_type
 AND c2.confidence > combined.confidence
);

CREATE INDEX idx_unified_lookup ON zone_setback_rules_unified (zone, council, boundary_type);
CREATE INDEX idx_unified_quality ON zone_setback_rules_unified (quality_tier, confidence DESC);
```

### Pros
- **Best of both worlds** - Single query point with quality preservation
- **Performance optimized** - Materialized view pre-computed
- **Quality filtering** - Can filter by tier if needed
- **No data loss** - Original tables preserved
- **Frontend simplicity** - Single endpoint

### Cons
- **Storage overhead** - Duplicates data in view
- **Refresh needed** - Must refresh materialized view on updates

## RECOMMENDATION: Option 1 (Combine) with Quality Tracking

```sql
-- 1. Add quality tier to main table
ALTER TABLE zone_setback_rules ADD COLUMN quality_tier VARCHAR(20);

-- 2. Merge comprehensive data
INSERT INTO zone_setback_rules 
SELECT * FROM zone_setback_rules_comprehensive
ON CONFLICT (rule_id) DO UPDATE SET
 confidence = GREATEST(EXCLUDED.confidence, zone_setback_rules.confidence),
 quality_tier = CASE 
 WHEN GREATEST(EXCLUDED.confidence, zone_setback_rules.confidence) >= 0.95 THEN 'verified'
 WHEN GREATEST(EXCLUDED.confidence, zone_setback_rules.confidence) >= 0.85 THEN 'high'
 ELSE 'medium'
 END;

-- 3. Frontend can optionally filter by quality
SELECT * FROM zone_setback_rules 
WHERE zone = 'R2' 
AND council = 'Marrickville'
AND quality_tier IN ('verified', 'high') -- Optional quality filter
ORDER BY confidence DESC, precedence_level ASC;
```

This gives us:
- Simple frontend (one table)
- Quality transparency (tier field)
- Performance (single query)
- Flexibility (can filter by quality if needed)