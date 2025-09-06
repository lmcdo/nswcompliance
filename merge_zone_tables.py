#!/usr/bin/env python3
"""
Merge zone_setback_rules_comprehensive into zone_setback_rules
Preserves highest confidence scores and adds quality tiers
"""

import psycopg2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def merge_zone_tables():
    """Merge comprehensive rules into main table with quality tracking"""
    
    conn = psycopg2.connect(
        host='localhost',
        database='nsw_planning', 
        user='postgres',
        password='postgres',
        port='5432'
    )
    cursor = conn.cursor()
    
    try:
        # 1. Add quality_tier column if it doesn't exist
        cursor.execute("""
            ALTER TABLE zone_setback_rules 
            ADD COLUMN IF NOT EXISTS quality_tier VARCHAR(20)
        """)
        logger.info("Added quality_tier column")
        
        # 2. Update existing rules with quality tiers
        cursor.execute("""
            UPDATE zone_setback_rules 
            SET quality_tier = CASE 
                WHEN confidence >= 0.95 THEN 'verified'
                WHEN confidence >= 0.85 THEN 'high'
                WHEN confidence >= 0.75 THEN 'medium'
                ELSE 'low'
            END
            WHERE quality_tier IS NULL
        """)
        logger.info("Updated quality tiers for existing rules")
        
        # 3. Count before merge
        cursor.execute("SELECT COUNT(*) FROM zone_setback_rules")
        before_count = cursor.fetchone()[0]
        logger.info(f"Rules before merge: {before_count}")
        
        # 4. Merge comprehensive rules, keeping highest confidence
        cursor.execute("""
            INSERT INTO zone_setback_rules (
                rule_id, zone, council, boundary_type, base_value, unit,
                operator, authority_type, precedence_level, conditions,
                source_document, source_clause, source_file, confidence, quality_tier
            )
            SELECT 
                rule_id, zone, council, boundary_type, base_value, unit,
                operator, authority_type, precedence_level, conditions,
                source_document, source_clause, source_file, confidence,
                CASE 
                    WHEN confidence >= 0.95 THEN 'verified'
                    WHEN confidence >= 0.85 THEN 'high'
                    WHEN confidence >= 0.75 THEN 'medium'
                    ELSE 'low'
                END as quality_tier
            FROM zone_setback_rules_comprehensive
            ON CONFLICT (rule_id) DO UPDATE SET
                confidence = GREATEST(EXCLUDED.confidence, zone_setback_rules.confidence),
                quality_tier = CASE 
                    WHEN GREATEST(EXCLUDED.confidence, zone_setback_rules.confidence) >= 0.95 THEN 'verified'
                    WHEN GREATEST(EXCLUDED.confidence, zone_setback_rules.confidence) >= 0.85 THEN 'high'
                    WHEN GREATEST(EXCLUDED.confidence, zone_setback_rules.confidence) >= 0.75 THEN 'medium'
                    ELSE 'low'
                END,
                base_value = COALESCE(EXCLUDED.base_value, zone_setback_rules.base_value),
                source_document = COALESCE(EXCLUDED.source_document, zone_setback_rules.source_document)
        """)
        
        # 5. Count after merge
        cursor.execute("SELECT COUNT(*) FROM zone_setback_rules")
        after_count = cursor.fetchone()[0]
        logger.info(f"Rules after merge: {after_count}")
        logger.info(f"New rules added: {after_count - before_count}")
        
        # 6. Create optimized indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_zone_rules_quality 
            ON zone_setback_rules (quality_tier, confidence DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_zone_rules_council_zone 
            ON zone_setback_rules (council, zone, boundary_type)
        """)
        logger.info("Created optimized indexes")
        
        # 7. Report merged statistics
        cursor.execute("""
            SELECT 
                quality_tier,
                COUNT(*) as count,
                COUNT(DISTINCT zone) as zones,
                COUNT(DISTINCT council) as councils
            FROM zone_setback_rules
            GROUP BY quality_tier
            ORDER BY 
                CASE quality_tier
                    WHEN 'verified' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    ELSE 4
                END
        """)
        
        print("\n=== MERGE COMPLETE ===")
        print("\nQuality Distribution:")
        for tier, count, zones, councils in cursor.fetchall():
            print(f"  {tier}: {count} rules, {zones} zones, {councils} councils")
        
        # 8. Coverage report
        cursor.execute("""
            SELECT council, COUNT(DISTINCT zone) as zones, COUNT(*) as rules
            FROM zone_setback_rules
            GROUP BY council
            ORDER BY council
        """)
        
        print("\nCouncil Coverage:")
        for council, zones, rules in cursor.fetchall():
            print(f"  {council}: {zones} zones, {rules} rules")
        
        # 9. Zone coverage
        cursor.execute("""
            SELECT DISTINCT zone 
            FROM zone_setback_rules 
            ORDER BY zone
        """)
        zones = [row[0] for row in cursor.fetchall()]
        print(f"\nTotal Zones Covered: {', '.join(zones)}")
        
        conn.commit()
        logger.info("Merge committed successfully")
        
        # 10. Optional: Archive comprehensive table
        cursor.execute("""
            ALTER TABLE zone_setback_rules_comprehensive 
            RENAME TO zone_setback_rules_comprehensive_archived
        """)
        logger.info("Archived comprehensive table")
        
        conn.commit()
        
    except Exception as e:
        logger.error(f"Error during merge: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
    
    return after_count

if __name__ == "__main__":
    total_rules = merge_zone_tables()
    print(f"\n✅ Successfully merged zone tables: {total_rules} total rules available")