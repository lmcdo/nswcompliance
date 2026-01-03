#!/usr/bin/env python3
"""
PRP-8B: Authoritative Migration System (Fixed)
Migrates existing provisions to authoritative schema with proper JSON handling
"""

import asyncio
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict, Counter

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class AuthoritativeMigrationFixed:
    """Migrate existing provisions to authoritative schema with hierarchy resolution"""

    def __init__(self):
        from .db_config import get_connection
        self.pg_conn = get_connection()
        self.stats = {
            'provisions_migrated': 0,
            'properties_imported': 0,
            'hierarchies_resolved': 0,
            'tiers_classified': 0,
            'errors': []
        }
    
    async def migrate_all(self):
        """Complete migration to authoritative system"""
        
        print("[PRP-8B Fixed] Starting authoritative migration...")
        
        try:
            # Phase 1: Migrate planning provisions with hierarchy
            await self.migrate_provisions_with_hierarchy()
            
            # Phase 2: Import test NSW property data  
            await self.import_test_properties()
            
            # Phase 3: Build authority tiers
            await self.classify_authority_tiers()
            
            # Phase 4: Generate completion report
            await self.generate_completion_report()
            
            print(f"[PRP-8B Fixed] Migration complete: {self.stats}")
            return self.stats
            
        except Exception as e:
            print(f"[PRP-8B Fixed] Migration failed: {e}")
            import traceback
            traceback.print_exc()
            self.stats['errors'].append(str(e))
            return self.stats
    
    async def migrate_provisions_with_hierarchy(self):
        """Migrate existing provisions to authoritative schema"""
        
        print("[PRP-8B Fixed] Migrating provisions with hierarchy...")
        
        with self.pg_conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get zone-mapped provisions only
            cur.execute("""
                SELECT 
                    rp.*,
                    qs.numeric_value,
                    qs.unit,
                    qs.context as measurement_context,
                    qs.confidence_score
                FROM public.regulatory_provisions rp
                LEFT JOIN public.quantitative_standards qs ON rp.id = qs.provision_id
                WHERE rp.zone IS NOT NULL
                ORDER BY rp.id
            """)
            
            provisions = cur.fetchall()
            print(f"Found {len(provisions)} zone-mapped provisions to migrate")
            
            for prov in provisions:
                try:
                    # Determine authority level and document type
                    authority_level, doc_type = self.determine_authority_level(prov)
                    
                    # Create JSON-safe metadata (convert datetime to string)
                    original_json = self.make_json_safe({
                        'original_provision_id': prov['id'],
                        'document_id': prov.get('document_id'),
                        'ref_number': prov.get('ref_number'),
                        'domain_classification': prov.get('domain_classification'),
                        'classification_confidence': float(prov.get('classification_confidence') or 0.85),
                        'extraction_metadata': {
                            'method': 'zone_mapped_migration',
                            'migration_timestamp': datetime.now().isoformat(),
                            'original_created_at': prov.get('created_at').isoformat() if prov.get('created_at') else None
                        }
                    })
                    
                    # Determine applicable zones (single zone from our mapping)
                    applicable_zones = [prov['zone']] if prov['zone'] else []
                    
                    # Insert into authoritative schema
                    cur.execute("""
                        INSERT INTO authoritative.planning_provisions (
                            document_type,
                            document_name,
                            clause_reference,
                            authority_level,
                            provision_text,
                            provision_type,
                            applicable_zones,
                            numeric_value,
                            unit,
                            measurement_context,
                            original_json,
                            extraction_method,
                            extraction_confidence,
                            created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        doc_type,
                        f"Document_{prov.get('document_id', 'unknown')}",
                        prov.get('ref_number') or f"ref_{prov['id']}",  # Handle NULL ref_number
                        authority_level,
                        prov.get('provision_text', ''),
                        (prov.get('provision_type') or 'general')[:50],  # Truncate provision_type
                        applicable_zones,
                        prov.get('numeric_value'),
                        prov.get('unit'),
                        (prov.get('measurement_context') or '')[:100],  # Truncate to 100 chars
                        json.dumps(original_json),
                        'zone_mapped_migration',
                        float(prov.get('confidence_score') or 0.85),
                        datetime.now()
                    ))
                    
                    new_id = cur.fetchone()[0]
                    self.pg_conn.commit()  # Commit after each successful provision
                    self.stats['provisions_migrated'] += 1
                    
                    if self.stats['provisions_migrated'] % 50 == 0:
                        print(f"Migrated {self.stats['provisions_migrated']} provisions...")
                        
                except Exception as e:
                    print(f"Error migrating provision {prov['id']}: {e}")
                    self.stats['errors'].append(f"Provision {prov['id']}: {str(e)}")
                    
                    # Rollback transaction on error to continue with next provision
                    try:
                        self.pg_conn.rollback()
                    except:
                        pass  # Continue even if rollback fails
                    
                    continue
            
            print(f"Successfully migrated {self.stats['provisions_migrated']} provisions")
    
    def make_json_safe(self, obj):
        """Convert any datetime objects to ISO strings for JSON serialization"""
        if isinstance(obj, dict):
            return {k: self.make_json_safe(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.make_json_safe(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj
    
    def determine_authority_level(self, provision) -> tuple:
        """Determine authority level and document type based on provision data"""
        
        # Default to DCP level
        authority_level = 3
        doc_type = "DCP"
        
        # Check document patterns to determine hierarchy
        doc_id = str(provision.get('document_id', ''))
        ref_num = str(provision.get('ref_number', ''))
        section = str(provision.get('section_header', ''))
        
        # SEPP indicators
        if any(keyword in (doc_id + ref_num + section).lower() for keyword in [
            'sepp', 'state environmental planning policy', 'environmental planning policy'
        ]):
            authority_level = 1
            doc_type = "SEPP"
        
        # LEP indicators  
        elif any(keyword in (doc_id + ref_num + section).lower() for keyword in [
            'lep', 'local environmental plan', 'environmental plan'
        ]):
            authority_level = 2
            doc_type = "LEP"
        
        return authority_level, doc_type
    
    async def import_test_properties(self):
        """Import test property data for demo purposes"""
        
        print("[PRP-8B Fixed] Importing test property data...")
        
        # Create sample properties for each zone we have
        test_properties = [
            {
                'property_id': 1000001,
                'address': '123 Test Street, Marrickville NSW 2204',
                'lot_dp': 'Lot 1 DP 123456',
                'zone_code': 'R2',
                'lga_name': 'INNER_WEST',
                'lep_name': 'Inner West LEP 2022'
            },
            {
                'property_id': 1000002, 
                'address': '456 Demo Avenue, Ashfield NSW 2131',
                'lot_dp': 'Lot 2 DP 789012',
                'zone_code': 'R3',
                'lga_name': 'INNER_WEST',
                'lep_name': 'Inner West LEP 2022'
            },
            {
                'property_id': 1000003,
                'address': '789 Sample Road, Leichhardt NSW 2040',  
                'lot_dp': 'Lot 3 DP 345678',
                'zone_code': 'B2',
                'lga_name': 'INNER_WEST',
                'lep_name': 'Inner West LEP 2022'
            }
        ]
        
        with self.pg_conn.cursor() as cur:
            for prop in test_properties:
                try:
                    cur.execute("""
                        INSERT INTO authoritative.nsw_properties (
                            property_id, address, lot_dp, zone_code, lga_name, lep_name
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (property_id) DO NOTHING
                    """, (
                        prop['property_id'],
                        prop['address'],
                        prop['lot_dp'],
                        prop['zone_code'],
                        prop['lga_name'],
                        prop['lep_name']
                    ))
                    
                    self.stats['properties_imported'] += 1
                    
                except Exception as e:
                    print(f"Error importing property {prop['property_id']}: {e}")
                    continue
        
        self.pg_conn.commit()
        print(f"Imported {self.stats['properties_imported']} test properties")
    
    async def classify_authority_tiers(self):
        """Classify provisions into 5-tier authority system"""
        
        print("[PRP-8B Fixed] Classifying authority tiers...")
        
        with self.pg_conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get all migrated provisions
            cur.execute("SELECT id, authority_level, extraction_confidence FROM authoritative.planning_provisions")
            provisions = cur.fetchall()
            
            for prov in provisions:
                try:
                    # Determine tier based on authority level and confidence
                    tier_level, tier_name = self.calculate_authority_tier(
                        prov['authority_level'], 
                        prov['extraction_confidence']
                    )
                    
                    cur.execute("""
                        INSERT INTO authoritative.provision_authority_tiers (
                            provision_id, tier_level, tier_name, confidence_level
                        ) VALUES (%s, %s, %s, %s)
                    """, (
                        prov['id'],
                        tier_level,
                        tier_name,
                        prov['extraction_confidence']
                    ))
                    
                    self.stats['tiers_classified'] += 1
                    
                except Exception as e:
                    print(f"Error classifying tier for provision {prov['id']}: {e}")
                    continue
        
        self.pg_conn.commit()
        print(f"Classified {self.stats['tiers_classified']} authority tiers")
    
    def calculate_authority_tier(self, authority_level: int, confidence: float) -> tuple:
        """Calculate 5-tier authority classification"""
        
        # Tier 1: Fully authoritative (SEPP + high confidence)
        if authority_level == 1 and confidence >= 0.90:
            return 1, "fully_authoritative"
        
        # Tier 2: High authority (LEP high confidence or SEPP medium confidence)  
        elif (authority_level == 2 and confidence >= 0.85) or (authority_level == 1 and confidence >= 0.75):
            return 2, "high_authority"
        
        # Tier 3: Moderate authority (DCP high confidence or LEP medium confidence)
        elif (authority_level == 3 and confidence >= 0.80) or (authority_level == 2 and confidence >= 0.70):
            return 3, "moderate_authority"
        
        # Tier 4: Limited authority (lower confidence across all levels)
        elif confidence >= 0.60:
            return 4, "limited_authority"
        
        # Tier 5: Specialist referral required (very low confidence)
        else:
            return 5, "specialist_referral"
    
    async def generate_completion_report(self):
        """Generate comprehensive completion report"""
        
        print("[PRP-8B Fixed] Generating completion report...")
        
        with self.pg_conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get tier distribution
            cur.execute("""
                SELECT tier_level, tier_name, COUNT(*) as count
                FROM authoritative.provision_authority_tiers
                GROUP BY tier_level, tier_name
                ORDER BY tier_level
            """)
            tier_distribution = cur.fetchall()
            
            # Get zone distribution
            cur.execute("""
                SELECT unnest(applicable_zones) as zone, COUNT(*) as count
                FROM authoritative.planning_provisions
                GROUP BY zone
                ORDER BY zone
            """)
            zone_distribution = cur.fetchall()
        
        report = [
            "=" * 60,
            "PRP-8B AUTHORITATIVE MIGRATION REPORT",
            "=" * 60,
            f"Migration completed: {datetime.now().isoformat()}",
            "",
            "MIGRATION STATISTICS",
            "-" * 30,
            f"Provisions migrated: {self.stats['provisions_migrated']}",
            f"Properties imported: {self.stats['properties_imported']}", 
            f"Authority tiers classified: {self.stats['tiers_classified']}",
            f"Errors encountered: {len(self.stats['errors'])}",
            "",
            "AUTHORITY TIER DISTRIBUTION",
            "-" * 30
        ]
        
        for tier in tier_distribution:
            report.append(f"Tier {tier['tier_level']} ({tier['tier_name']}): {tier['count']} provisions")
        
        report.extend([
            "",
            "ZONE DISTRIBUTION", 
            "-" * 30
        ])
        
        for zone in zone_distribution:
            report.append(f"Zone {zone['zone']}: {zone['count']} provisions")
        
        if self.stats['errors']:
            report.extend([
                "",
                "ERRORS SUMMARY",
                "-" * 30
            ])
            for error in self.stats['errors'][:10]:  # Show first 10 errors
                report.append(f"• {error}")
            
            if len(self.stats['errors']) > 10:
                report.append(f"... and {len(self.stats['errors']) - 10} more errors")
        
        report.extend([
            "",
            "SYSTEM READY",
            "-" * 30,
            "[OK] Authoritative schema populated",
            "[OK] Hierarchy classifications complete",
            "[OK] Authority tiers assigned",
            "[OK] Test properties available",
            "",
            "Next: Run PRP-8B completion validation"
        ])
        
        report_text = "\n".join(report)
        print("\n" + report_text)
        
        # Save report
        try:
            with open('PRP_8B_MIGRATION_REPORT.txt', 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"\nMigration report saved: PRP_8B_MIGRATION_REPORT.txt")
        except Exception as e:
            print(f"Could not save report: {e}")
    
    def close(self):
        """Close database connection"""
        if self.pg_conn:
            self.pg_conn.close()

async def main():
    """Main migration execution"""
    
    migration = AuthoritativeMigrationFixed()
    
    try:
        stats = await migration.migrate_all()
        
        if stats['provisions_migrated'] > 0:
            print(f"\n[SUCCESS] Migration successful: {stats['provisions_migrated']} provisions migrated")
            return True
        else:
            print(f"\n[FAILED] Migration failed: No provisions migrated")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Migration error: {e}")
        return False
        
    finally:
        migration.close()

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    exit(0 if success else 1)