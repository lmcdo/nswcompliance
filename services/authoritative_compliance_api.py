#!/usr/bin/env python3
"""
PRP-8B: Authoritative Compliance API
Provides authoritative compliance checking with 5-tier confidence system
"""

import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, asdict

@dataclass
class AuthoritativeProvision:
    clause_reference: str
    document_source: str
    authority_level: str
    provision_text: str
    numeric_value: Optional[float]
    unit: Optional[str]
    confidence_level: float
    tier: int
    tier_name: str
    professional_required: bool
    specialist_type: Optional[str]
    boundary_type: Optional[str] = None
    conditions: Optional[Dict] = None

@dataclass
class PropertySummary:
    property_id: int
    address: str
    zone_code: str
    lga_name: str
    height_limit: Optional[float]
    fsr_limit: Optional[float]
    heritage_status: Optional[str]
    data_source: str = "NSW_PLANNING_PORTAL"

@dataclass
class AuthoritativeComplianceResponse:
    property: PropertySummary
    tier_1_provisions: List[AuthoritativeProvision]
    tier_2_provisions: List[AuthoritativeProvision]
    tier_3_provisions: List[AuthoritativeProvision]
    tier_4_provisions: List[AuthoritativeProvision]
    tier_5_provisions: List[AuthoritativeProvision]
    primary_authorities: Dict[str, AuthoritativeProvision]
    complexity_assessment: str
    professional_guidance: List[str]
    specialist_referrals: List[Dict]
    data_currency: str
    confidence_level: float
    legal_disclaimer: str

class HierarchyResolver:
    """Resolve legal hierarchy for authoritative responses"""
    
    def __init__(self, db_conn):
        self.db = db_conn
    
    def resolve_hierarchy(
        self,
        zone: str,
        dev_type: str,
        requirement: str,
        boundary: Optional[str] = None
    ) -> Optional[Dict]:
        """Resolve hierarchy for specific requirement"""
        
        # Build cache key
        cache_key = f"{zone}:{dev_type}:{requirement}:{boundary or 'any'}"
        
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            # Try cache first
            cur.execute("""
                SELECT 
                    primary_provision_id,
                    authority_chain,
                    resolution_method,
                    resolution_confidence
                FROM authoritative.hierarchy_resolution_cache
                WHERE cache_key = %s AND expires_at > NOW()
            """, (cache_key,))
            
            cached = cur.fetchone()
            
            if cached:
                # Update hit count
                cur.execute("""
                    UPDATE authoritative.hierarchy_resolution_cache
                    SET hit_count = hit_count + 1
                    WHERE cache_key = %s
                """, (cache_key,))
                
                # Get full provision details
                cur.execute("""
                    SELECT p.*, t.tier_level, t.confidence_level, t.tier_name, t.professional_required, t.specialist_type
                    FROM authoritative.planning_provisions p
                    JOIN authoritative.provision_authority_tiers t ON p.id = t.provision_id
                    WHERE p.id = %s
                """, (cached['primary_provision_id'],))
                
                provision = cur.fetchone()
                
                if provision:
                    return {
                        'primary_provision': dict(provision),
                        'resolution_method': cached['resolution_method'],
                        'confidence': cached['resolution_confidence'],
                        'cached': True
                    }
            
            # No cache - resolve live
            cur.execute("""
                SELECT 
                    p.*,
                    t.tier_level,
                    t.confidence_level,
                    t.tier_name,
                    t.professional_required,
                    t.specialist_type
                FROM authoritative.planning_provisions p
                JOIN authoritative.provision_authority_tiers t ON p.id = t.provision_id
                WHERE %s = ANY(p.applicable_zones)
                AND (p.applicable_dev_types IS NULL OR %s = ANY(p.applicable_dev_types) OR 'general' = ANY(p.applicable_dev_types))
                AND (p.provision_type = %s OR p.provision_type IS NULL)
                AND (p.boundary_type = %s OR %s IS NULL OR p.boundary_type IS NULL)
                ORDER BY p.authority_level, p.numeric_value DESC NULLS LAST
                LIMIT 10
            """, (zone, dev_type, requirement, boundary, boundary))
            
            provisions = cur.fetchall()
            
            if not provisions:
                return None
            
            # Select primary by hierarchy
            primary = provisions[0]
            
            # Cache result
            cur.execute("""
                INSERT INTO authoritative.hierarchy_resolution_cache (
                    cache_key, primary_provision_id, authority_chain,
                    resolution_method, resolution_confidence
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (cache_key) DO UPDATE
                SET primary_provision_id = EXCLUDED.primary_provision_id,
                    hit_count = 0
            """, (
                cache_key,
                primary['id'],
                json.dumps([p['id'] for p in provisions]),
                self.determine_resolution_method(provisions),
                primary['confidence_level']
            ))
            
            self.db.commit()
            
            return {
                'primary_provision': dict(primary),
                'all_provisions': [dict(p) for p in provisions],
                'resolution_method': self.determine_resolution_method(provisions),
                'confidence': primary['confidence_level'],
                'cached': False
            }
    
    def determine_resolution_method(self, provisions: List[Dict]) -> str:
        """Determine how hierarchy was resolved"""
        if not provisions:
            return 'no_provisions'
        
        primary = provisions[0]
        
        if primary['document_type'] == 'SEPP':
            return 'sepp_override'
        elif primary['document_type'] == 'LEP':
            return 'lep_standard'
        elif len(provisions) > 1:
            return 'hierarchy_precedence'
        else:
            return 'single_source'

class AuthoritativeComplianceAPI:
    """Main authoritative compliance API"""
    
    def __init__(self):
        self.db = psycopg2.connect(
            host="localhost",
            database="nsw_planning",
            user="postgres",
            password="postgres"
        )
        self.resolver = HierarchyResolver(self.db)
    
    def check_compliance(
        self,
        property_id: Optional[int] = None,
        property_address: Optional[str] = None,
        zone_code: Optional[str] = None,
        development_type: Optional[str] = None,
        requirement_type: Optional[str] = None
    ) -> Dict:
        """Main authoritative compliance check"""
        
        try:
            # Get property data
            property_data = self.get_property_data(property_id, property_address, zone_code)
            
            if not property_data:
                return {
                    'error': 'Property not found',
                    'message': 'Property not found in NSW Planning Portal data'
                }
            
            # Get applicable provisions by tier
            provisions_by_tier = self.get_provisions_by_tier(
                property_data['zone_code'],
                development_type or 'dwelling_house',
                requirement_type
            )
            
            # Resolve hierarchy for primary authorities
            primary_authorities = {}
            
            # Common requirement types
            requirement_types = ['setback', 'height', 'fsr', 'parking'] if not requirement_type else [requirement_type]
            
            for req_type in requirement_types:
                if req_type == 'setback':
                    # Resolve for each boundary
                    for boundary in ['front', 'rear', 'side']:
                        resolution = self.resolver.resolve_hierarchy(
                            property_data['zone_code'],
                            development_type or 'dwelling_house',
                            req_type,
                            boundary
                        )
                        if resolution:
                            key = f"{req_type}_{boundary}"
                            primary_authorities[key] = self.convert_to_authoritative_provision(
                                resolution['primary_provision']
                            )
                else:
                    resolution = self.resolver.resolve_hierarchy(
                        property_data['zone_code'],
                        development_type or 'dwelling_house',
                        req_type
                    )
                    if resolution:
                        primary_authorities[req_type] = self.convert_to_authoritative_provision(
                            resolution['primary_provision']
                        )
            
            # Generate professional guidance
            guidance = self.generate_professional_guidance(
                property_data,
                provisions_by_tier,
                primary_authorities
            )
            
            # Create response
            response = AuthoritativeComplianceResponse(
                property=PropertySummary(**property_data),
                tier_1_provisions=provisions_by_tier.get(1, []),
                tier_2_provisions=provisions_by_tier.get(2, []),
                tier_3_provisions=provisions_by_tier.get(3, []),
                tier_4_provisions=provisions_by_tier.get(4, []),
                tier_5_provisions=provisions_by_tier.get(5, []),
                primary_authorities=primary_authorities,
                complexity_assessment=guidance['complexity'],
                professional_guidance=guidance['recommendations'],
                specialist_referrals=guidance['referrals'],
                data_currency=f"Live as of {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                confidence_level=self.calculate_overall_confidence(provisions_by_tier),
                legal_disclaimer=self.generate_legal_disclaimer(provisions_by_tier)
            )
            
            return asdict(response)
            
        except Exception as e:
            return {
                'error': 'System error',
                'message': f'Compliance check failed: {str(e)}'
            }
    
    def get_property_data(
        self,
        property_id: Optional[int],
        address: Optional[str],
        zone_code: Optional[str]
    ) -> Optional[Dict]:
        """Get property data from NSW Planning Portal or cache"""
        
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            if property_id:
                cur.execute("""
                    SELECT * FROM authoritative.nsw_properties
                    WHERE property_id = %s
                """, (property_id,))
                result = cur.fetchone()
                
            elif address:
                cur.execute("""
                    SELECT * FROM authoritative.nsw_properties
                    WHERE address ILIKE %s
                    LIMIT 1
                """, (f"%{address}%",))
                result = cur.fetchone()
                
            elif zone_code:
                # Create synthetic property for zone-only queries
                return {
                    'property_id': 0,
                    'address': f'Example property in {zone_code} zone',
                    'zone_code': zone_code,
                    'lga_name': 'EXAMPLE_LGA',
                    'height_limit': None,
                    'fsr_limit': None,
                    'heritage_status': 'Unknown'
                }
                
            else:
                return None
            
            return dict(result) if result else None
    
    def get_provisions_by_tier(
        self,
        zone_code: str,
        development_type: str,
        requirement_type: Optional[str] = None
    ) -> Dict[int, List[AuthoritativeProvision]]:
        """Get applicable provisions grouped by tier"""
        
        provisions_by_tier = {1: [], 2: [], 3: [], 4: [], 5: []}
        
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            # Build query conditions
            where_conditions = [
                "%s = ANY(p.applicable_zones)",
                "(%s = ANY(p.applicable_dev_types) OR 'general' = ANY(p.applicable_dev_types))"
            ]
            params = [zone_code, development_type]
            
            if requirement_type:
                where_conditions.append("p.provision_type = %s")
                params.append(requirement_type)
            
            query = f"""
                SELECT 
                    p.*,
                    t.tier_level,
                    t.tier_name,
                    t.confidence_level,
                    t.professional_required,
                    t.specialist_type
                FROM authoritative.planning_provisions p
                JOIN authoritative.provision_authority_tiers t ON p.id = t.provision_id
                WHERE {' AND '.join(where_conditions)}
                ORDER BY t.tier_level, p.authority_level, p.numeric_value DESC NULLS LAST
                LIMIT 50
            """
            
            cur.execute(query, params)
            provisions = cur.fetchall()
            
            for prov in provisions:
                tier = prov['tier_level']
                if tier in provisions_by_tier:
                    provisions_by_tier[tier].append(
                        self.convert_to_authoritative_provision(prov)
                    )
        
        return provisions_by_tier
    
    def convert_to_authoritative_provision(self, prov: Dict) -> AuthoritativeProvision:
        """Convert database row to AuthoritativeProvision"""
        
        return AuthoritativeProvision(
            clause_reference=prov.get('clause_reference', 'No reference'),
            document_source=prov.get('document_name', 'Unknown document'),
            authority_level=prov.get('document_type', 'OTHER'),
            provision_text=prov.get('provision_text', '')[:200] + ('...' if len(prov.get('provision_text', '')) > 200 else ''),
            numeric_value=prov.get('numeric_value'),
            unit=prov.get('unit'),
            confidence_level=prov.get('confidence_level', 0.5),
            tier=prov.get('tier_level', 4),
            tier_name=prov.get('tier_name', 'unknown'),
            professional_required=prov.get('professional_required', True),
            specialist_type=prov.get('specialist_type'),
            boundary_type=prov.get('boundary_type'),
            conditions=json.loads(prov.get('conditions', '{}')) if prov.get('conditions') else None
        )
    
    def generate_professional_guidance(
        self,
        property_data: Dict,
        provisions_by_tier: Dict,
        primary_authorities: Dict
    ) -> Dict:
        """Generate professional guidance based on complexity"""
        
        # Determine complexity
        tier_5_count = len(provisions_by_tier.get(5, []))
        tier_4_count = len(provisions_by_tier.get(4, []))
        tier_3_count = len(provisions_by_tier.get(3, []))
        
        if tier_5_count > 0:
            complexity = 'EXTREME - Specialist referral essential'
        elif tier_4_count > 2:
            complexity = 'HIGH - Professional assessment required'
        elif tier_3_count > 3:
            complexity = 'MODERATE - Professional interpretation recommended'
        else:
            complexity = 'LOW - Standard provisions apply'
        
        # Generate recommendations
        recommendations = []
        referrals = []
        
        if tier_5_count > 0:
            recommendations.append("DO NOT PROCEED without specialist consultation")
            recommendations.append("Complex environmental or heritage assessment required")
            referrals.append({
                'specialist_type': 'environmental_consultant',
                'urgency': 'critical',
                'reason': 'Tier 5 provisions detected'
            })
        
        if tier_4_count > 0:
            recommendations.append("Engage qualified town planner for assessment")
            recommendations.append("Consider pre-DA consultation with council")
        
        if 'heritage' in property_data.get('heritage_status', '').lower():
            recommendations.append("Heritage impact assessment may be required")
            referrals.append({
                'specialist_type': 'heritage_consultant',
                'urgency': 'high',
                'reason': 'Heritage constraints identified'
            })
        
        if not recommendations:
            recommendations = [
                "Standard development provisions apply",
                "Professional verification recommended for development applications"
            ]
        
        return {
            'complexity': complexity,
            'recommendations': recommendations,
            'referrals': referrals
        }
    
    def calculate_overall_confidence(self, provisions_by_tier: Dict) -> float:
        """Calculate overall confidence based on tier distribution"""
        
        tier_weights = {
            1: 1.00,  # Fully authoritative
            2: 0.85,  # High authority
            3: 0.70,  # Moderate authority
            4: 0.50,  # Framework guidance
            5: 0.30   # Referral required
        }
        
        total_weight = 0
        total_provisions = 0
        
        for tier, provisions in provisions_by_tier.items():
            count = len(provisions)
            total_provisions += count
            total_weight += count * tier_weights.get(tier, 0.5)
        
        if total_provisions == 0:
            return 0.5
        
        return total_weight / total_provisions
    
    def generate_legal_disclaimer(self, provisions_by_tier: Dict) -> str:
        """Generate appropriate legal disclaimer based on confidence"""
        
        if provisions_by_tier.get(5):  # Tier 5 present
            return """
            SPECIALIST REFERRAL REQUIRED: This query involves complex environmental, 
            heritage, or multi-agency requirements that exceed automated assessment scope. 
            Professional specialist consultation is essential before proceeding.
            """
        elif provisions_by_tier.get(4):  # Tier 4 present
            return """
            PROFESSIONAL GUIDANCE RECOMMENDED: While framework guidance is provided, 
            site-specific professional assessment is strongly recommended for 
            development application preparation.
            """
        elif provisions_by_tier.get(3):  # Tier 3 present
            return """
            PROFESSIONAL INTERPRETATION MAY BE REQUIRED: Some provisions require 
            site-specific interpretation. Consider professional planning consultation 
            for complex sites or variations.
            """
        elif provisions_by_tier.get(2):  # Tier 2 only
            return """
            HIGH CONFIDENCE GUIDANCE: Based on authoritative government sources. 
            Professional verification recommended for development applications.
            """
        else:  # Tier 1 only
            return """
            AUTHORITATIVE GOVERNMENT DATA: Sourced directly from NSW Planning Portal 
            and gazetted planning instruments. Suitable for professional reliance 
            with appropriate verification.
            """

# Flask/FastAPI integration example
def create_api_endpoint():
    """Create API endpoint for testing"""
    
    api = AuthoritativeComplianceAPI()
    
    def compliance_check_endpoint():
        """Example endpoint usage"""
        
        # Example 1: Property ID lookup
        result1 = api.check_compliance(property_id=3597448)
        print("Property ID lookup result:")
        print(json.dumps(result1, indent=2, default=str))
        
        # Example 2: Zone-only query
        result2 = api.check_compliance(
            zone_code='R2',
            development_type='dwelling_house',
            requirement_type='setback'
        )
        print("\nZone query result:")
        print(json.dumps(result2, indent=2, default=str))
        
        return result1, result2
    
    return compliance_check_endpoint

if __name__ == "__main__":
    print("[PRP-8B] Testing Authoritative Compliance API...")
    
    # Test the API
    test_endpoint = create_api_endpoint()
    test_endpoint()
    
    print("[PRP-8B] API test completed")