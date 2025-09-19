#!/usr/bin/env python3
"""
PRP-K8: Zone Assignment Verification Suite
Uses existing NSW Planning API to validate zone inferences
"""

import asyncio
import aiohttp
import sqlite3
import json
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote
import time

class PlanningAPIValidator:
    """Validates zone assignments using NSW Planning API"""
    
    def __init__(self, db_path: str = "nsw_planning.db"):
        self.db_path = db_path
        self.base_url = "https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi"
        self.valuation_url = "https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer/5/query"
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_property_zone(self, address: str) -> Optional[Dict]:
        """Get authoritative zone data for an address using Planning API"""
        
        try:
            # Step 1: Get property ID from address
            address_url = f"{self.base_url}/address?a={quote(address)}&noOfRecords=1"
            
            async with self.session.get(address_url) as response:
                if response.status != 200:
                    print(f"Address lookup failed for {address}: {response.status}")
                    return None
                    
                address_data = await response.json()
                if not address_data:
                    print(f"No property found for address: {address}")
                    return None
                
                prop_id = address_data[0].get('propId')
                if not prop_id:
                    print(f"No property ID found for: {address}")
                    return None
            
            # Step 2: Get zoning and development control data
            layer_url = f"{self.base_url}/layerintersect?type=property&id={prop_id}&layers=epi"
            
            async with self.session.get(layer_url) as response:
                if response.status != 200:
                    print(f"Layer lookup failed for property {prop_id}: {response.status}")
                    return None
                    
                layer_data = await response.json()
                
                # Extract zone information
                zone_info = {
                    'address': address,
                    'prop_id': prop_id,
                    'zone': None,
                    'land_use': None,
                    'height_limit': None,
                    'fsr_limit': None,
                    'heritage': None,
                    'lga': None
                }
                
                for layer in layer_data:
                    layer_name = layer.get('layerName', '')
                    results = layer.get('results', [])
                    
                    if not results:
                        continue
                        
                    result = results[0]  # Take first result
                    
                    if 'Land Zoning Map' in layer_name:
                        zone_info['zone'] = result.get('Zone')
                        zone_info['land_use'] = result.get('Land Use')
                        zone_info['lga'] = result.get('LGA Name')
                        
                    elif 'Height of Buildings Map' in layer_name:
                        height = result.get('Maximum Building Height')
                        units = result.get('Units', 'm')
                        if height:
                            zone_info['height_limit'] = f"{height}{units}"
                            
                    elif 'Floor Space Ratio Map' in layer_name:
                        fsr = result.get('Floor Space Ratio')
                        if fsr:
                            zone_info['fsr_limit'] = f"{fsr}:1"
                            
                    elif 'Heritage Map' in layer_name:
                        heritage_type = result.get('Heritage Type')
                        item_name = result.get('Item Name') 
                        if heritage_type and item_name:
                            zone_info['heritage'] = f"{heritage_type}: {item_name}"
                
                return zone_info
                
        except Exception as e:
            print(f"Error validating address {address}: {e}")
            return None
    
    def get_sample_provisions_for_validation(self, limit: int = 100) -> List[Dict]:
        """Get sample provisions with inferred zones for validation"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get provisions with zones and some geographic/address context
        cursor.execute("""
            SELECT id, provision_type, zone, provision_text, document_id, ref_number
            FROM regulatory_provisions 
            WHERE zone IS NOT NULL AND zone != ''
            AND (provision_text LIKE '%Street%' 
                 OR provision_text LIKE '%Road%' 
                 OR provision_text LIKE '%Avenue%'
                 OR provision_text LIKE '%Drive%'
                 OR provision_text LIKE '%Marrickville%'
                 OR provision_text LIKE '%Leichhardt%'
                 OR provision_text LIKE '%Ashfield%'
                 OR provision_text LIKE '%Drummoyne%'
                 OR provision_text LIKE '%Balmain%')
            ORDER BY RANDOM()
            LIMIT ?
        """, (limit,))
        
        provisions = []
        for row in cursor.fetchall():
            provisions.append({
                'id': row[0],
                'provision_type': row[1], 
                'inferred_zone': row[2],
                'provision_text': row[3],
                'document_id': row[4],
                'ref_number': row[5]
            })
        
        conn.close()
        return provisions

class ZoneVerificationSuite:
    """Complete verification suite for zone assignments"""
    
    def __init__(self, db_path: str = "nsw_planning.db"):
        self.db_path = db_path
        self.results = {
            'verified_count': 0,
            'validation_success': 0,
            'zone_matches': 0,
            'zone_mismatches': 0,
            'api_failures': 0,
            'total_checked': 0,
            'accuracy_by_method': {},
            'mismatch_details': []
        }
    
    async def run_full_verification(self, sample_size: int = 100) -> Dict:
        """Run complete verification suite"""
        
        print(f"🔍 Starting Zone Verification Suite")
        print(f"📊 Sample size: {sample_size} provisions")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        async with PlanningAPIValidator(self.db_path) as validator:
            # Get sample provisions
            provisions = validator.get_sample_provisions_for_validation(sample_size)
            print(f"📋 Retrieved {len(provisions)} provisions for validation")
            
            # Extract addresses from provision text
            validated_count = 0
            
            for i, provision in enumerate(provisions, 1):
                print(f"⚡ Validating provision {i}/{len(provisions)}: {provision['ref_number']}")
                
                # Try to extract address from provision text
                addresses = self.extract_addresses_from_text(provision['provision_text'])
                
                if not addresses:
                    print(f"  ⚠️  No addresses found in text")
                    continue
                
                # Test first address found
                address = addresses[0]
                print(f"  📍 Testing address: {address}")
                
                # Get zone data from API
                zone_data = await validator.get_property_zone(address)
                
                if not zone_data:
                    self.results['api_failures'] += 1
                    print(f"  ❌ API validation failed")
                    continue
                
                # Compare zones
                api_zone = zone_data.get('zone')
                inferred_zone = provision['inferred_zone']
                
                print(f"  🎯 Inferred: {inferred_zone}, API: {api_zone}")
                
                if api_zone:
                    self.results['validation_success'] += 1
                    validated_count += 1
                    
                    if api_zone == inferred_zone:
                        self.results['zone_matches'] += 1
                        print(f"  ✅ MATCH")
                    else:
                        self.results['zone_mismatches'] += 1
                        print(f"  ⚠️  MISMATCH")
                        
                        # Record mismatch details
                        self.results['mismatch_details'].append({
                            'provision_id': provision['id'],
                            'ref_number': provision['ref_number'], 
                            'inferred_zone': inferred_zone,
                            'api_zone': api_zone,
                            'address': address,
                            'provision_type': provision['provision_type']
                        })
                
                # Rate limiting
                await asyncio.sleep(0.2)  # 200ms delay between requests
                
                self.results['total_checked'] += 1
        
        # Calculate final metrics
        if self.results['validation_success'] > 0:
            accuracy = self.results['zone_matches'] / self.results['validation_success']
            self.results['accuracy_percentage'] = accuracy * 100
        else:
            self.results['accuracy_percentage'] = 0
            
        return self.results
    
    def extract_addresses_from_text(self, text: str) -> List[str]:
        """Extract potential addresses from provision text"""
        import re
        
        addresses = []
        
        # Pattern for street addresses 
        street_pattern = r'(\d+\s+[A-Za-z\s]+(?:Street|Road|Avenue|Drive|Lane|Place|Crescent|Circuit|Way|Close|Court)(?:\s+\w+)*)'
        matches = re.findall(street_pattern, text, re.IGNORECASE)
        
        for match in matches:
            # Add suburb context if missing
            if 'Marrickville' not in match and 'Leichhardt' not in match and 'Ashfield' not in match:
                # Try to infer suburb from document
                if 'Marrickville' in text:
                    addresses.append(f"{match}, Marrickville NSW 2204")
                elif 'Leichhardt' in text: 
                    addresses.append(f"{match}, Leichhardt NSW 2040")
                elif 'Ashfield' in text:
                    addresses.append(f"{match}, Ashfield NSW 2131")
            else:
                addresses.append(match)
        
        return addresses[:3]  # Return max 3 addresses
    
    def generate_verification_report(self) -> str:
        """Generate detailed verification report"""
        
        report = f"""
🔍 ZONE VERIFICATION SUITE - RESULTS REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 VALIDATION SUMMARY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total provisions checked:     {self.results['total_checked']:,}
Successfully validated:       {self.results['validation_success']:,}
API validation failures:      {self.results['api_failures']:,}

🎯 ZONE MATCHING ACCURACY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Zone matches:                 {self.results['zone_matches']:,}
Zone mismatches:             {self.results['zone_mismatches']:,}
Overall accuracy:            {self.results['accuracy_percentage']:.1f}%

"""
        
        if self.results['mismatch_details']:
            report += "\n⚠️  ZONE MISMATCHES (First 10):\n"
            report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            
            for i, mismatch in enumerate(self.results['mismatch_details'][:10], 1):
                report += f"{i}. [{mismatch['ref_number']}] {mismatch['provision_type']}\n"
                report += f"   Inferred: {mismatch['inferred_zone']} | API: {mismatch['api_zone']}\n"
                report += f"   Address: {mismatch['address']}\n\n"
        
        report += "\n🎯 RECOMMENDATIONS:\n"
        report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        if self.results['accuracy_percentage'] >= 90:
            report += "✅ Zone inference accuracy is EXCELLENT (>90%)\n"
            report += "   → Ready for production deployment\n"
        elif self.results['accuracy_percentage'] >= 75:
            report += "⚠️  Zone inference accuracy is GOOD (75-90%)\n" 
            report += "   → Consider improving inference algorithms\n"
        else:
            report += "❌ Zone inference accuracy is LOW (<75%)\n"
            report += "   → Requires significant algorithm improvements\n"
        
        if self.results['api_failures'] > 20:
            report += "⚠️  High API failure rate - consider rate limiting\n"
            
        return report

async def main():
    """Run zone verification suite"""
    
    suite = ZoneVerificationSuite()
    
    # Run verification with sample size
    results = await suite.run_full_verification(sample_size=50)
    
    # Generate and display report
    report = suite.generate_verification_report()
    print(report)
    
    # Save results to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"zone_verification_report_{timestamp}.json"
    
    with open(report_file, 'w') as f:
        json.dump({
            'results': results,
            'report': report,
            'timestamp': timestamp
        }, f, indent=2, default=str)
    
    print(f"📄 Detailed results saved to: {report_file}")

if __name__ == "__main__":
    asyncio.run(main())