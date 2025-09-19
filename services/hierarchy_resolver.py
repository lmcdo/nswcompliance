#!/usr/bin/env python3
"""
PRP-8B CHUNK 3: HierarchyResolver Service
Implements authority hierarchy resolution with SEPP > LEP > DCP precedence
Based on PRP-8B lines 590-687
"""

import json
import psycopg2
import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class HierarchyResolver:
    """Core hierarchy resolution engine with caching"""
    
    def __init__(self, db_pool=None):
        if db_pool:
            self.db_pool = db_pool
        else:
            # Create direct connection for standalone usage using environment variables
            self.pg_conn = psycopg2.connect(
                host=os.getenv('PGHOST', 'localhost'),
                port=int(os.getenv('PGPORT', 5432)),
                database=os.getenv('PGDATABASE', 'nsw_planning'),
                user=os.getenv('PGUSER', 'postgres'),
                password=os.getenv('PGPASSWORD', 'postgres')
            )
    
    def get_cache_key(self, query_params: Dict) -> str:
        """Generate cache key from query parameters"""
        # Sort keys for consistent cache keys
        sorted_params = json.dumps(query_params, sort_keys=True)
        return hashlib.md5(sorted_params.encode()).hexdigest()
    
    def check_cache(self, cache_key: str) -> Optional[Dict]:
        """Check hierarchy resolution cache"""
        
        with self.pg_conn.cursor() as cur:
            cur.execute("""
                SELECT authority_chain, created_at
                FROM authoritative.hierarchy_resolution_cache
                WHERE cache_key = %s
                AND (expires_at IS NULL OR expires_at > %s)
            """, (cache_key, datetime.now()))
            
            result = cur.fetchone()
            if result:
                authority_chain, created_at = result
                # Update hit count
                cur.execute("""
                    UPDATE authoritative.hierarchy_resolution_cache 
                    SET hit_count = hit_count + 1
                    WHERE cache_key = %s
                """, (cache_key,))
                self.pg_conn.commit()
                
                # authority_chain is already a dict from JSONB column
                return authority_chain if authority_chain else None
        
        return None
    
    def store_cache(self, cache_key: str, result: Dict):
        """Store result in hierarchy cache"""
        
        with self.pg_conn.cursor() as cur:
            # Get primary provision ID if available
            primary_provision_id = None
            if result.get('primary_authorities'):
                # Use first primary authority's provision
                for context, auth in result['primary_authorities'].items():
                    if 'provision_id' in auth:
                        primary_provision_id = auth['provision_id']
                        break
            
            cur.execute("""
                INSERT INTO authoritative.hierarchy_resolution_cache (
                    cache_key, primary_provision_id, authority_chain, 
                    resolution_method, resolution_confidence, created_at, 
                    expires_at, hit_count
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (cache_key) 
                DO UPDATE SET 
                    authority_chain = EXCLUDED.authority_chain,
                    resolution_confidence = EXCLUDED.resolution_confidence,
                    created_at = EXCLUDED.created_at,
                    expires_at = EXCLUDED.expires_at
            """, (
                cache_key,
                primary_provision_id,
                json.dumps(result),
                result.get('complexity_assessment', 'standard'),
                result.get('confidence_level', 0.75),
                datetime.now(),
                datetime.now() + timedelta(hours=24),  # 24 hour cache
                0  # Initial hit count
            ))
            
            self.pg_conn.commit()
    
    def get_provisions_for_property(self, zone_code: str, development_type: str = None) -> List[Dict]:
        """Get all applicable provisions for property"""
        
        with self.pg_conn.cursor() as cur:
            query = """
                SELECT 
                    pp.id,
                    pp.document_type,
                    pp.document_name,
                    pp.clause_reference,
                    pp.authority_level,
                    pp.provision_text,
                    pp.provision_type,
                    pp.applicable_zones,
                    pp.applicable_dev_types,
                    pp.numeric_value,
                    pp.unit,
                    pp.measurement_context,
                    pp.boundary_type,
                    pp.extraction_confidence,
                    pat.tier_level,
                    pat.tier_name,
                    pat.confidence_level
                FROM authoritative.planning_provisions pp
                JOIN authoritative.provision_authority_tiers pat ON pp.id = pat.provision_id
                WHERE %s = ANY(pp.applicable_zones)
            """
            
            params = [zone_code]
            
            if development_type:
                query += " AND (%s = ANY(pp.applicable_dev_types) OR array_length(pp.applicable_dev_types, 1) IS NULL)"
                params.append(development_type)
            
            query += " ORDER BY pp.authority_level ASC, pat.tier_level ASC, pp.extraction_confidence DESC"
            
            cur.execute(query, params)
            
            provisions = []
            for row in cur.fetchall():
                provisions.append({
                    'id': row[0],
                    'document_type': row[1], 
                    'document_name': row[2],
                    'clause_reference': row[3],
                    'authority_level': row[4],
                    'provision_text': row[5],
                    'provision_type': row[6],
                    'applicable_zones': row[7],
                    'applicable_dev_types': row[8],
                    'numeric_value': float(row[9]) if row[9] else None,
                    'unit': row[10],
                    'measurement_context': row[11],
                    'boundary_type': row[12],
                    'extraction_confidence': float(row[13]) if row[13] else None,
                    'tier_level': row[14],
                    'tier_name': row[15],
                    'confidence_level': float(row[16]) if row[16] else None
                })
            
            return provisions
    
    def group_provisions_by_tier(self, provisions: List[Dict]) -> Dict[str, List[Dict]]:
        """Group provisions by authority tier"""
        
        tiers = {
            'tier_1_provisions': [],
            'tier_2_provisions': [], 
            'tier_3_provisions': [],
            'tier_4_provisions': [],
            'tier_5_provisions': []
        }
        
        for provision in provisions:
            tier_level = provision.get('tier_level', 5)
            tier_key = f'tier_{tier_level}_provisions'
            
            if tier_key in tiers:
                tiers[tier_key].append(provision)
        
        return tiers
    
    def select_primary_authority(self, provisions: List[Dict], measurement_context: str) -> Optional[Dict]:
        """Select primary authority for specific measurement context using hierarchy"""
        
        # Filter provisions for this measurement context
        relevant_provisions = [
            p for p in provisions 
            if p.get('measurement_context') == measurement_context
            and p.get('numeric_value') is not None
        ]
        
        if not relevant_provisions:
            return None
        
        # Sort by authority level (1=SEPP highest, 3=DCP lowest) then confidence
        relevant_provisions.sort(key=lambda p: (
            p.get('authority_level', 5),
            -p.get('confidence_level', 0)
        ))
        
        primary = relevant_provisions[0]
        
        return {
            'document_type': primary['document_type'],
            'document_name': primary['document_name'],
            'clause_reference': primary['clause_reference'],
            'authority_level': primary['authority_level'],
            'numeric_value': primary['numeric_value'],
            'unit': primary['unit'],
            'confidence_level': primary['confidence_level'],
            'tier_level': primary['tier_level'],
            'overrides_count': len([p for p in relevant_provisions if p['authority_level'] > primary['authority_level']])
        }
    
    def resolve_primary_authorities(self, provisions: List[Dict]) -> Dict[str, Dict]:
        """Resolve primary authorities for each measurement context"""
        
        # Get all unique measurement contexts
        contexts = set(p.get('measurement_context') for p in provisions if p.get('measurement_context'))
        
        primary_authorities = {}
        
        for context in contexts:
            primary = self.select_primary_authority(provisions, context)
            if primary:
                primary_authorities[context] = primary
        
        return primary_authorities
    
    def assess_complexity(self, provisions: List[Dict], primary_authorities: Dict) -> Tuple[str, float]:
        """Assess compliance complexity and confidence"""
        
        total_provisions = len(provisions)
        tier_1_count = len([p for p in provisions if p.get('tier_level') == 1])
        tier_5_count = len([p for p in provisions if p.get('tier_level') == 5])
        
        # Calculate average confidence
        confidences = [p.get('confidence_level', 0) for p in provisions if p.get('confidence_level')]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        # Determine complexity
        if tier_5_count > total_provisions * 0.3:
            complexity = "high_complexity_specialist_required"
            confidence = min(avg_confidence, 0.6)
        elif tier_1_count > total_provisions * 0.5:
            complexity = "low_complexity_statutory_clear"  
            confidence = max(avg_confidence, 0.9)
        elif total_provisions > 20:
            complexity = "medium_complexity_multiple_provisions"
            confidence = avg_confidence * 0.8
        else:
            complexity = "moderate_complexity_standard_process"
            confidence = avg_confidence
        
        return complexity, min(confidence, 1.0)
    
    def generate_legal_disclaimer(self, complexity: str, tier_distribution: Dict) -> str:
        """Generate appropriate legal disclaimer based on complexity"""
        
        tier_5_count = tier_distribution.get('tier_5_provisions', 0)
        tier_1_count = tier_distribution.get('tier_1_provisions', 0) 
        
        if tier_5_count > 0:
            return "SPECIALIST CONSULTATION REQUIRED: This assessment contains provisions requiring professional interpretation. Seek qualified planning consultant advice before proceeding."
        elif tier_1_count > 3:
            return "STATUTORY PROVISIONS APPLY: This assessment is based on authoritative statutory requirements. Professional verification recommended for complex applications."
        elif complexity == "high_complexity_specialist_required":
            return "COMPLEX ASSESSMENT: Multiple overlapping provisions identified. Professional planning advice strongly recommended."
        else:
            return "INDICATIVE ASSESSMENT: This preliminary assessment provides guidance only. Verify with local council before lodging development application."
    
    def resolve_hierarchy(self, zone_code: str, property_id: int = None, development_type: str = None) -> Dict:
        """Main hierarchy resolution method"""
        
        # Generate cache key
        cache_params = {
            'zone_code': zone_code,
            'property_id': property_id,
            'development_type': development_type,
            'version': 'chunk3_v1'
        }
        cache_key = self.get_cache_key(cache_params)
        
        # Check cache first
        cached_result = self.check_cache(cache_key)
        if cached_result:
            cached_result['cache_hit'] = True
            return cached_result
        
        # Get applicable provisions
        provisions = self.get_provisions_for_property(zone_code, development_type)
        
        # Group by tier
        tier_groups = self.group_provisions_by_tier(provisions)
        
        # Resolve primary authorities
        primary_authorities = self.resolve_primary_authorities(provisions)
        
        # Assess complexity
        complexity, confidence = self.assess_complexity(provisions, primary_authorities)
        
        # Count tier distribution for disclaimer
        tier_counts = {key: len(provisions) for key, provisions in tier_groups.items()}
        
        # Generate legal disclaimer
        legal_disclaimer = self.generate_legal_disclaimer(complexity, tier_counts)
        
        # Build response
        result = {
            'property': {
                'property_id': property_id,
                'zone_code': zone_code,
                'development_type': development_type
            },
            **tier_groups,
            'primary_authorities': primary_authorities,
            'complexity_assessment': complexity,
            'confidence_level': confidence,
            'legal_disclaimer': legal_disclaimer,
            'processing_metadata': {
                'total_provisions_found': len(provisions),
                'tier_distribution': tier_counts,
                'processing_time': datetime.now().isoformat(),
                'cache_hit': False
            }
        }
        
        # Cache the result
        self.store_cache(cache_key, result)
        
        return result
    
    def close(self):
        """Clean up database connections"""
        if hasattr(self, 'pg_conn'):
            self.pg_conn.close()

# Test the HierarchyResolver independently
if __name__ == "__main__":
    resolver = HierarchyResolver()
    
    try:
        # Test with R2 zone
        result = resolver.resolve_hierarchy("R2", property_id=1, development_type="dwelling_house")
        
        print("HIERARCHY RESOLVER TEST:")
        print(f"Total provisions: {result['processing_metadata']['total_provisions_found']}")
        print(f"Primary authorities: {len(result['primary_authorities'])}")
        print(f"Complexity: {result['complexity_assessment']}")
        print(f"Confidence: {result['confidence_level']:.2f}")
        print(f"Tier distribution: {result['processing_metadata']['tier_distribution']}")
        
        # Test caching
        print("\nTesting cache...")
        start_time = datetime.now()
        cached_result = resolver.resolve_hierarchy("R2", property_id=1, development_type="dwelling_house") 
        cache_time = (datetime.now() - start_time).total_seconds()
        
        print(f"Cache hit: {cached_result.get('cache_hit', False)}")
        print(f"Cache retrieval time: {cache_time:.3f} seconds")
        
    finally:
        resolver.close()