#!/usr/bin/env python3
"""
PRP-8B: Authoritative Migration System
Migrates existing provisions to authoritative schema with hierarchy resolution
"""

import asyncio
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict, Counter

class AuthoritativeMigration:
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
            'properties_imported': 0,
            'hierarchies_resolved': 0,
            'tiers_classified': 0,
            'errors': []
        }
    
    async def migrate_all(self):
        """Complete migration to authoritative system"""
        
        print("[PRP-8B] Starting authoritative migration...")
        
        try:
            # Phase 1: Migrate planning provisions with hierarchy
            await self.migrate_provisions_with_hierarchy()
            
            # Phase 2: Import test NSW property data
            await self.import_test_properties()
            
            # Phase 3: Build authority tiers
            await self.classify_authority_tiers()
            
            # Phase 4: Pre-compute hierarchy resolutions
            await self.precompute_hierarchy_resolutions()
            
            # Phase 5: Generate professional guidance
            await self.generate_professional_guidance()
            
            print(f"[PRP-8B] Migration complete: {self.stats}")
            return self.stats
            
        except Exception as e:
            print(f"[PRP-8B] Migration failed: {e}")
            self.stats['errors'].append(str(e))
            return self.stats
    
    async def migrate_provisions_with_hierarchy(self):
        """Migrate existing provisions to authoritative schema"""
        
        print("[PRP-8B] Migrating provisions with hierarchy...")
        
        with self.pg_conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get existing provisions with JSON data
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
                LIMIT 1000
            """)
            
            provisions = cur.fetchall()
            
            for prov in provisions:
                try:
                    # Determine authority level
                    authority_level = self.determine_authority_level(prov)
                    
                    # Preserve JSON richness
                    original_json = {
                        'original_provision': dict(prov),
                        'extraction_metadata': {
                            'method': prov.get('extraction_method', 'legacy'),
                            'timestamp': prov.get('created_at', datetime.now()).isoformat() if prov.get('created_at') else datetime.now().isoformat()
                        }
                    }
                    
                    # Insert into authoritative schema
                    cur.execute("""
                        INSERT INTO authoritative.planning_provisions (
                            document_type, document_name, clause_reference,
                            authority_level, provision_text, provision_type,
                            applicable_zones, applicable_lgas, applicable_dev_types,
                            numeric_value, unit, measurement_context, boundary_type,
                            original_json, extraction_confidence, verification_status
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT DO NOTHING
                    """, (
                        self.extract_document_type(prov),
                        prov.get('document_name', '') or 'Unknown Document',
                        prov.get('ref_number', '') or 'No Reference',
                        authority_level,
                        prov.get('provision_text', '') or 'No text available',
                        prov.get('provision_type', 'other'),
                        [prov.get('zone')] if prov.get('zone') else ['UNKNOWN'],
                        self.extract_lgas(prov),
                        [prov.get('development_type')] if prov.get('development_type') else ['general'],
                        prov.get('numeric_value'),
                        prov.get('unit') or 'm',
                        prov.get('measurement_context'),
                        self.extract_boundary_type(prov),
                        json.dumps(original_json),
                        prov.get('confidence_score') or 0.75,
                        'migrated'
                    ))
                    
                    self.stats['provisions_migrated'] += 1
                    
                except Exception as e:
                    error_msg = f"Error migrating provision {prov.get('id', 'unknown')}: {e}"
                    print(f"Warning: {error_msg}")
                    self.stats['errors'].append(error_msg)
                    continue
                
        self.pg_conn.commit()
        print(f"[PRP-8B] Migrated {self.stats['provisions_migrated']} provisions")
    
    def determine_authority_level(self, provision: Dict) -> int:
        """Determine legal hierarchy level"""
        doc_name = (provision.get('document_name') or '').upper()
        
        if 'SEPP' in doc_name:
            return 1
        elif 'LEP' in doc_name:
            return 2
        elif 'DCP' in doc_name:
            return 3
        else:
            return 4  # Unknown/other
    
    def extract_document_type(self, provision: Dict) -> str:
        """Extract document type from provision"""
        doc_name = (provision.get('document_name') or '').upper()
        
        if 'SEPP' in doc_name:
            return 'SEPP'
        elif 'LEP' in doc_name:
            return 'LEP'
        elif 'DCP' in doc_name:
            return 'DCP'
        else:
            return 'OTHER'
    
    def extract_lgas(self, provision: Dict) -> List[str]:
        """Extract applicable LGAs"""
        doc_name = (provision.get('document_name') or '').upper()
        
        if 'INNER WEST' in doc_name or 'MARRICKVILLE' in doc_name or 'LEICHHARDT' in doc_name or 'ASHFIELD' in doc_name:
            return ['INNER_WEST']
        elif 'CANTERBURY' in doc_name or 'BANKSTOWN' in doc_name:
            return ['CANTERBURY_BANKSTOWN']
        else:
            return ['UNKNOWN']
    
    def extract_boundary_type(self, provision: Dict) -> Optional[str]:
        """Extract boundary type from context"""
        context = (provision.get('measurement_context') or '').lower()
        text = (provision.get('provision_text') or '').lower()
        
        if 'front' in context or 'front' in text:
            return 'front'
        elif 'rear' in context or 'back' in context or 'rear' in text:
            return 'rear'
        elif 'side' in context or 'side' in text:
            return 'side'
        else:
            return None
    
    async def import_test_properties(self):
        """Import test property data (using example from NSW Portal output)"""
        
        print("[PRP-8B] Importing test property data...")
        
        test_properties = [
            {
                'property_id': 3597448,
                'address': '34 Pile St, Dulwich Hill NSW 2203, Australia',
                'lot_dp': 'Unknown',
                'zone_code': 'R4',
                'lga_name': 'CANTERBURY-BANKSTOWN',
                'lep_name': 'Canterbury-Bankstown Local Environmental Plan 2023',
                'height_limit': 10.0,
                'fsr_limit': 1.5
            },
            {
                'property_id': 1234567,
                'address': '123 King Street, Newtown NSW 2042',
                'lot_dp': 'Lot 1 DP123456',
                'zone_code': 'R3',
                'lga_name': 'INNER_WEST',
                'lep_name': 'Inner West Local Environmental Plan 2022',
                'height_limit': 9.5,
                'fsr_limit': 0.8
            }
        ]
        
        with self.pg_conn.cursor() as cur:
            for prop in test_properties:
                try:
                    cur.execute("""
                        INSERT INTO authoritative.nsw_properties (
                            property_id, address, lot_dp, zone_code, lga_name,
                            lep_name, height_limit, fsr_limit, heritage_status
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (property_id) DO UPDATE SET
                            last_synced = NOW()
                    """, (
                        prop['property_id'],
                        prop['address'],
                        prop['lot_dp'],
                        prop['zone_code'],
                        prop['lga_name'],
                        prop['lep_name'],
                        prop['height_limit'],
                        prop['fsr_limit'],
                        'No heritage constraints'
                    ))
                    
                    self.stats['properties_imported'] += 1
                    
                except Exception as e:
                    error_msg = f"Error importing property {prop['property_id']}: {e}"
                    print(f"Warning: {error_msg}")
                    self.stats['errors'].append(error_msg)
        
        self.pg_conn.commit()
        print(f"[PRP-8B] Imported {self.stats['properties_imported']} test properties")
    
    async def classify_authority_tiers(self):
        """Classify provisions into authority tiers"""
        
        print("[PRP-8B] Classifying authority tiers...")
        
        with self.pg_conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, document_type, provision_type, numeric_value, extraction_confidence FROM authoritative.planning_provisions")
            provisions = cur.fetchall()
            
            for prov in provisions:
                try:
                    tier_level, confidence = self.determine_tier(prov)
                    
                    cur.execute("""
                        INSERT INTO authoritative.provision_authority_tiers (
                            provision_id, tier_level, tier_name, confidence_level,
                            professional_required, specialist_type
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (provision_id) DO UPDATE SET
                            tier_level = EXCLUDED.tier_level,
                            confidence_level = EXCLUDED.confidence_level
                    """, (
                        prov['id'],
                        tier_level,
                        self.get_tier_name(tier_level),
                        confidence,
                        tier_level >= 3,  # Professional required for tier 3+
                        self.get_specialist_type(prov)
                    ))
                    
                    self.stats['tiers_classified'] += 1
                    
                except Exception as e:
                    error_msg = f"Error classifying tier for provision {prov['id']}: {e}"
                    print(f"Warning: {error_msg}")
                    self.stats['errors'].append(error_msg)
            
        self.pg_conn.commit()
        print(f"[PRP-8B] Classified {self.stats['tiers_classified']} authority tiers")
    
    def determine_tier(self, provision: Dict) -> tuple:
        """Determine authority tier and confidence"""
        
        # Tier 1: Direct statutory values from SEPP/LEP
        if provision['document_type'] in ['SEPP', 'LEP'] and provision['numeric_value']:
            return 1, 1.00
        
        # Tier 2: DCP with clear measurements
        elif provision['document_type'] == 'DCP' and provision['numeric_value']:
            return 2, 0.85
        
        # Tier 3: Qualitative provisions requiring interpretation
        elif provision['numeric_value'] is None:
            return 3, 0.70
        
        # Tier 4: Low confidence provisions
        elif provision.get('extraction_confidence', 1.0) < 0.75:
            return 4, 0.60
        
        # Default
        return 2, 0.75
    
    def get_tier_name(self, tier: int) -> str:
        """Get tier name"""
        return {
            1: 'fully_authoritative',
            2: 'high_authority', 
            3: 'moderate_authority',
            4: 'framework_guidance',
            5: 'referral_required'
        }.get(tier, 'unknown')
    
    def get_specialist_type(self, provision: Dict) -> Optional[str]:
        """Determine specialist type required"""
        prov_type = provision.get('provision_type', '').lower()
        
        if 'heritage' in prov_type:
            return 'heritage_consultant'
        elif 'traffic' in prov_type or 'parking' in prov_type:
            return 'traffic_engineer'
        elif 'environment' in prov_type:
            return 'environmental_consultant'
        else:
            return None

    async def precompute_hierarchy_resolutions(self):
        """Pre-compute common hierarchy resolutions for performance"""
        
        print("[PRP-8B] Pre-computing hierarchy resolutions...")
        
        common_queries = [
            ('R1', 'dwelling_house', 'setback', 'front'),
            ('R2', 'dwelling_house', 'setback', 'front'),
            ('R2', 'dwelling_house', 'setback', 'rear'),
            ('R2', 'dwelling_house', 'setback', 'side'),
            ('R3', 'multi_dwelling_housing', 'setback', 'front'),
            ('R4', 'residential_flat_building', 'height', None),
        ]
        
        with self.pg_conn.cursor(cursor_factory=RealDictCursor) as cur:
            for zone, dev_type, req_type, boundary in common_queries:
                try:
                    cache_key = f"{zone}:{dev_type}:{req_type}:{boundary or 'any'}"
                    
                    # Find all applicable provisions
                    cur.execute("""
                        SELECT id, authority_level, numeric_value, document_type, extraction_confidence
                        FROM authoritative.planning_provisions
                        WHERE %s = ANY(applicable_zones)
                        AND (%s = ANY(applicable_dev_types) OR 'general' = ANY(applicable_dev_types))
                        AND provision_type = %s
                        AND (boundary_type = %s OR %s IS NULL OR boundary_type IS NULL)
                        ORDER BY authority_level, numeric_value DESC NULLS LAST
                        LIMIT 10
                    """, (zone, dev_type, req_type, boundary, boundary))
                    
                    provisions = cur.fetchall()
                    
                    if provisions:
                        # Select primary by hierarchy
                        primary = provisions[0]
                        
                        cur.execute("""
                            INSERT INTO authoritative.hierarchy_resolution_cache (
                                cache_key, primary_provision_id, authority_chain,
                                resolution_method, resolution_confidence
                            ) VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (cache_key) DO UPDATE
                            SET primary_provision_id = EXCLUDED.primary_provision_id,
                                authority_chain = EXCLUDED.authority_chain
                        """, (
                            cache_key,
                            primary['id'],
                            json.dumps([p['id'] for p in provisions]),
                            self.determine_resolution_method(provisions),
                            primary.get('extraction_confidence', 0.75)
                        ))
                        
                        self.stats['hierarchies_resolved'] += 1
                        
                except Exception as e:
                    error_msg = f"Error resolving hierarchy for {cache_key}: {e}"
                    print(f"Warning: {error_msg}")
                    self.stats['errors'].append(error_msg)
        
        self.pg_conn.commit()
        print(f"[PRP-8B] Pre-computed {self.stats['hierarchies_resolved']} hierarchy resolutions")
    
    def determine_resolution_method(self, provisions: List[Dict]) -> str:
        """Determine how hierarchy was resolved"""
        if not provisions:
            return 'no_provisions'
        
        primary = provisions[0]
        
        if primary['document_type'] == 'SEPP':
            return 'sepp_override'
        elif primary['document_type'] == 'LEP':
            return 'lep_standard'
        elif len(provisions) > 1 and provisions[0].get('numeric_value', 0) and provisions[1].get('numeric_value', 0):
            if provisions[0]['numeric_value'] > provisions[1]['numeric_value']:
                return 'most_restrictive'
        
        return 'single_source'
    
    async def generate_professional_guidance(self):
        """Generate professional guidance templates"""
        
        print("[PRP-8B] Generating professional guidance...")
        
        guidance_templates = [
            {
                'scenario_type': 'heritage_overlay',
                'guidance_text': 'Heritage Conservation Area overlay detected. Professional heritage assessment required to determine if standard controls apply or heritage-specific provisions override.',
                'complexity_level': 'high',
                'specialists_required': ['heritage_consultant', 'town_planner'],
                'typical_timeline': '6-12 weeks',
                'applicable_zones': ['R1', 'R2', 'R3', 'B1', 'B2']
            },
            {
                'scenario_type': 'standard_residential',
                'guidance_text': 'Standard residential development in established zone. Clear statutory controls apply with limited variation required.',
                'complexity_level': 'low',
                'specialists_required': ['town_planner'],
                'typical_timeline': '4-8 weeks',
                'applicable_zones': ['R1', 'R2', 'R3', 'R4']
            },
            {
                'scenario_type': 'subdivision_proposed',
                'guidance_text': 'Subdivision requires comprehensive assessment including services, traffic, and statutory compliance. Early council consultation recommended.',
                'complexity_level': 'medium',
                'specialists_required': ['town_planner', 'surveyor', 'civil_engineer'],
                'typical_timeline': '12-20 weeks',
                'applicable_zones': ['R1', 'R2', 'R3', 'R4']
            }
        ]
        
        with self.pg_conn.cursor() as cur:
            for template in guidance_templates:
                try:
                    cur.execute("""
                        INSERT INTO authoritative.professional_guidance (
                            scenario_type, guidance_text, complexity_level,
                            specialists_required, typical_timeline, applicable_zones
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        template['scenario_type'],
                        template['guidance_text'],
                        template['complexity_level'],
                        template['specialists_required'],
                        template['typical_timeline'],
                        template['applicable_zones']
                    ))
                    
                except Exception as e:
                    error_msg = f"Error creating guidance template: {e}"
                    print(f"Warning: {error_msg}")
                    self.stats['errors'].append(error_msg)
        
        self.pg_conn.commit()
        print("[PRP-8B] Professional guidance templates created")

if __name__ == "__main__":
    async def main():
        migration = AuthoritativeMigration()
        await migration.migrate_all()
    
    print("[PRP-8B] Starting PRP-8B migration...")
    asyncio.run(main())
    print("[PRP-8B] Migration script completed")