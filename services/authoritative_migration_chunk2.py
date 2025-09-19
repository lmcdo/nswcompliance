#!/usr/bin/env python3
"""
PRP-8B CHUNK 2: Authoritative Data Migration
Migrate regulatory provisions from public to authoritative schema with tier classification
Based on PRP-8B lines 224-528
"""

import psycopg2
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class AuthoritativeMigrationChunk2:
    """Migrate existing provisions to authoritative schema with hierarchy resolution"""
    
    def __init__(self):
        self.pg_conn = psycopg2.connect(
            host="localhost",
            database="nsw_planning",
            user="postgres",
            password="postgres"
        )
        self.stats = {
            'provisions_migrated': 0,
            'tiers_created': 0,
            'errors': [],
            'authority_distribution': {}
        }
        
    def determine_authority_level(self, document_id: str, provision: Dict) -> int:
        """Determine legal authority level from document ID (PRP-8B lines 341-352)"""
        doc_name = document_id.upper() if document_id else ''
        
        if 'STATE_ENVIRONMENTAL' in doc_name or 'SEPP' in doc_name:
            return 1  # SEPP - highest authority
        elif 'LOCAL_ENVIRONMENTAL' in doc_name or '_LEP_' in doc_name:
            return 2  # LEP - medium authority  
        elif 'DCP' in doc_name or 'DEVELOPMENT_CONTROL' in doc_name:
            return 3  # DCP - lowest authority
        else:
            return 4  # Unknown/other
    
    def extract_document_type(self, document_id: str) -> str:
        """Extract document type from document ID (PRP-8B lines 354-365)"""
        if not document_id:
            return 'OTHER'
            
        doc_name = document_id.upper()
        
        if 'STATE_ENVIRONMENTAL' in doc_name or 'SEPP' in doc_name:
            return 'SEPP'
        elif 'LOCAL_ENVIRONMENTAL' in doc_name or '_LEP_' in doc_name:
            return 'LEP'
        elif 'DCP' in doc_name or 'DEVELOPMENT_CONTROL' in doc_name:
            return 'DCP'
        else:
            return 'OTHER'
    
    def extract_lgas(self, document_id: str) -> List[str]:
        """Extract applicable LGAs (PRP-8B lines 367-376)"""
        if not document_id:
            return []
            
        doc_name = document_id.upper()
        
        if 'INNER_WEST' in doc_name or 'MARRICKVILLE' in doc_name:
            return ['INNER_WEST']
        elif 'CANTERBURY' in doc_name or 'BANKSTOWN' in doc_name:
            return ['CANTERBURY_BANKSTOWN']
        else:
            return []
    
    def extract_boundary_type(self, provision: Dict) -> Optional[str]:
        """Extract boundary type from context (PRP-8B lines 378-389)"""
        context = provision.get('measurement_context', '') or ''
        context_lower = context.lower()
        
        if 'front' in context_lower:
            return 'front'
        elif 'rear' in context_lower or 'back' in context_lower:
            return 'rear'
        elif 'side' in context_lower:
            return 'side'
        else:
            return None
    
    def determine_tier(self, authority_level: int, has_numeric_value: bool, provision_text: str) -> Tuple[int, float, str]:
        """Determine authority tier and confidence (PRP-8B lines 418-434)"""
        
        # Tier 1: Direct statutory values
        if authority_level <= 2 and has_numeric_value:
            return 1, 1.00, 'fully_authoritative'
        
        # Tier 2: DCP with clear measurements
        elif authority_level == 3 and has_numeric_value:
            return 2, 0.85, 'high_authority'
        
        # Tier 3: Qualitative provisions requiring interpretation
        elif not has_numeric_value:
            confidence = 0.70 if len(provision_text or '') > 50 else 0.60
            return 3, confidence, 'moderate_authority'
        
        # Tier 4: Framework guidance
        else:
            return 4, 0.60, 'framework_guidance'
    
    def migrate_provisions_with_hierarchy(self):
        """Migrate existing provisions to authoritative schema (PRP-8B lines 275-339)"""
        
        print("MIGRATING PROVISIONS WITH HIERARCHY")
        print("-" * 40)
        
        # Set autocommit to handle individual provision errors
        self.pg_conn.autocommit = True
        
        with self.pg_conn.cursor() as cur:
            # Get existing provisions with quantitative data
            cur.execute("""
                SELECT 
                    rp.id,
                    rp.zone,
                    rp.development_type,
                    rp.provision_text,
                    rp.ref_number,
                    rp.document_id,
                    rp.section_header,
                    rp.provision_type,
                    rp.confidence_score,
                    qs.numeric_value,
                    qs.unit,
                    qs.context as measurement_context
                FROM public.regulatory_provisions rp
                LEFT JOIN public.quantitative_standards qs ON rp.id = qs.provision_id
                WHERE rp.zone IS NOT NULL
            """)
            
            provisions = cur.fetchall()
            
            for prov in provisions:
                try:
                    prov_id, zone, dev_type, text, ref_num, doc_id, section, prov_type, confidence, numeric_value, unit, measurement_context = prov
                    
                    # Determine authority level
                    authority_level = self.determine_authority_level(doc_id, {})
                    
                    # Track authority distribution
                    doc_type = self.extract_document_type(doc_id)
                    self.stats['authority_distribution'][doc_type] = self.stats['authority_distribution'].get(doc_type, 0) + 1
                    
                    # Preserve JSON richness (PRP-8B lines 298-305) - Convert Decimal to float for JSON serialization
                    original_json = {
                        'source_provision_id': prov_id,
                        'extraction_metadata': {
                            'method': 'public_schema_migration',
                            'timestamp': datetime.now().isoformat(),
                            'source_schema': 'public'
                        },
                        'original_provision': {
                            'zone': zone,
                            'development_type': dev_type,
                            'provision_text': text,
                            'ref_number': ref_num,
                            'document_id': doc_id,
                            'section_header': section,
                            'provision_type': prov_type,
                            'confidence_score': float(confidence) if confidence is not None else None,
                            'numeric_value': float(numeric_value) if numeric_value is not None else None,
                            'unit': unit,
                            'measurement_context': measurement_context
                        }
                    }
                    
                    # Insert into authoritative schema with ON CONFLICT handling
                    cur.execute("""
                        INSERT INTO authoritative.planning_provisions (
                            document_type, document_name, clause_reference,
                            authority_level, provision_text, provision_type,
                            applicable_zones, applicable_lgas, applicable_dev_types,
                            numeric_value, unit, measurement_context, boundary_type,
                            original_json, extraction_method, extraction_confidence, verification_status
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT DO NOTHING
                        RETURNING id
                    """, (
                        self.extract_document_type(doc_id),
                        doc_id or '',
                        ref_num or '',
                        authority_level,
                        text or '',
                        prov_type or 'other',
                        [zone] if zone else [],
                        self.extract_lgas(doc_id or ''),
                        [dev_type] if dev_type else [],
                        numeric_value,
                        unit or 'm',
                        measurement_context,
                        self.extract_boundary_type({'measurement_context': measurement_context}),
                        json.dumps(original_json),
                        'public_schema_migration',
                        confidence or 0.75,
                        'migrated'
                    ))
                    
                    result = cur.fetchone()
                    if result:
                        new_provision_id = result[0]
                        self.stats['provisions_migrated'] += 1
                    else:
                        # Conflict occurred, skip tier creation
                        continue
                    
                    # Create tier classification
                    has_numeric = numeric_value is not None
                    tier_level, tier_confidence, tier_name = self.determine_tier(authority_level, has_numeric, text or '')
                    
                    cur.execute("""
                        INSERT INTO authoritative.provision_authority_tiers (
                            provision_id, tier_level, tier_name, confidence_level,
                            professional_required, specialist_type
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        new_provision_id,
                        tier_level,
                        tier_name,
                        tier_confidence,
                        tier_level >= 3,  # Professional required for tier 3+
                        self.get_specialist_type(prov_type or '')
                    ))
                    
                    self.stats['tiers_created'] += 1
                    
                    if self.stats['provisions_migrated'] % 50 == 0:
                        print(f"Progress: {self.stats['provisions_migrated']}/{len(provisions)}")
                        
                except Exception as e:
                    error_msg = f"Provision {prov_id if 'prov_id' in locals() else 'unknown'}: {str(e)}"
                    self.stats['errors'].append(error_msg)
                    print(f"ERROR: {error_msg}")
                    continue
            
            # Already auto-committing individual provisions
    
    def get_specialist_type(self, provision_type: str) -> Optional[str]:
        """Determine specialist type required (PRP-8B lines 446-457)"""
        prov_type = provision_type.lower()
        
        if 'heritage' in prov_type:
            return 'heritage_consultant'
        elif 'traffic' in prov_type or 'parking' in prov_type:
            return 'traffic_engineer'
        elif 'environment' in prov_type:
            return 'environmental_consultant'
        else:
            return None
    
    def verify_migration_integrity(self):
        """Verify migration completed successfully"""
        
        print("\nVERIFYING MIGRATION INTEGRITY")
        print("-" * 40)
        
        with self.pg_conn.cursor() as cur:
            # Check source count
            cur.execute("SELECT COUNT(*) FROM public.regulatory_provisions WHERE zone IS NOT NULL")
            source_count = cur.fetchone()[0]
            
            # Check target count
            cur.execute("SELECT COUNT(*) FROM authoritative.planning_provisions")
            target_count = cur.fetchone()[0]
            
            # Check tier count
            cur.execute("SELECT COUNT(*) FROM authoritative.provision_authority_tiers")
            tier_count = cur.fetchone()[0]
            
            # Check authority distribution
            cur.execute("""
                SELECT document_type, COUNT(*) 
                FROM authoritative.planning_provisions 
                GROUP BY document_type 
                ORDER BY document_type
            """)
            auth_distribution = dict(cur.fetchall())
            
            # Check tier distribution
            cur.execute("""
                SELECT tier_level, COUNT(*) 
                FROM authoritative.provision_authority_tiers 
                GROUP BY tier_level 
                ORDER BY tier_level
            """)
            tier_distribution = dict(cur.fetchall())
            
            print(f"Source provisions: {source_count}")
            print(f"Target provisions: {target_count}")
            print(f"Tiers created: {tier_count}")
            print(f"Authority distribution: {auth_distribution}")
            print(f"Tier distribution: {tier_distribution}")
            
            # Validation checks
            migration_rate = target_count / source_count if source_count > 0 else 0
            print(f"Migration rate: {migration_rate:.1%}")
            
            success = migration_rate >= 0.8 and tier_count > 0
            return success, {
                'source_count': source_count,
                'target_count': target_count,
                'tier_count': tier_count,
                'migration_rate': migration_rate,
                'authority_distribution': auth_distribution,
                'tier_distribution': tier_distribution
            }
    
    def run_migration(self):
        """Execute complete migration process"""
        
        print("PRP-8B CHUNK 2: AUTHORITATIVE DATA MIGRATION")
        print("=" * 60)
        
        try:
            # Phase 1: Migrate provisions with hierarchy
            self.migrate_provisions_with_hierarchy()
            
            # Phase 2: Verify migration integrity
            success, results = self.verify_migration_integrity()
            
            print("\n" + "=" * 60)
            print("MIGRATION COMPLETE")
            print(f"Success: {success}")
            print(f"Provisions migrated: {self.stats['provisions_migrated']}")
            print(f"Tiers created: {self.stats['tiers_created']}")
            print(f"Errors: {len(self.stats['errors'])}")
            
            if self.stats['errors']:
                print("Error details:")
                for error in self.stats['errors'][:5]:  # Show first 5 errors
                    print(f"  - {error}")
            
            return success, results
            
        except Exception as e:
            print(f"MIGRATION FAILED: {e}")
            return False, {'error': str(e)}
        
        finally:
            self.pg_conn.close()

if __name__ == "__main__":
    migrator = AuthoritativeMigrationChunk2()
    success, results = migrator.run_migration()
    exit(0 if success else 1)