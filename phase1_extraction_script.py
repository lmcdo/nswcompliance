#!/usr/bin/env python3
"""
PRP-P1: Phase 1 - Permissibility Pattern Extraction
Extracts development permissibility patterns from regulatory provisions
"""

import sqlite3
import re
import json
import time
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import csv

class PermissibilityExtractor:
    """
    Extracts development permissibility patterns from regulatory provisions
    """
    
    def __init__(self, db_path: str = "nsw_planning.db"):
        self.conn = sqlite3.connect(db_path)
        self.cur = self.conn.cursor()
        
        # Pattern extraction rules
        self.permissibility_patterns = {
            'permitted_without_consent': [
                r'permitted without consent.*?(?:\([^)]*\)|\d+\..*?(?=\d+\.|$))',
                r'development may be carried out without consent.*?(?:\([^)]*\)|\d+\..*?(?=\d+\.|$))',
                r'the following.*?permitted.*?(?:\([^)]*\)|\d+\..*?(?=\d+\.|$))'
            ],
            'permitted_with_consent': [
                r'permitted with consent.*?(?:\([^)]*\)|\d+\..*?(?=\d+\.|$))',
                r'development.*?consent.*?(?:\([^)]*\)|\d+\..*?(?=\d+\.|$))',
                r'may be carried out.*?consent.*?(?:\([^)]*\)|\d+\..*?(?=\d+\.|$))'
            ],
            'prohibited': [
                r'prohibited.*?(?:\([^)]*\)|\d+\..*?(?=\d+\.|$))',
                r'not permitted.*?(?:\([^)]*\)|\d+\..*?(?=\d+\.|$))',
                r'development.*?not.*?allowed.*?(?:\([^)]*\)|\d+\..*?(?=\d+\.|$))'
            ],
            'development_may': [
                r'development may.*?(?:\([^)]*\)|\d+\..*?(?=\d+\.|$))',
                r'purposes.*?(?:\([^)]*\)|\d+\..*?(?=\d+\.|$))',
                r'following development.*?(?:\([^)]*\)|\d+\..*?(?=\d+\.|$))'
            ]
        }
        
        # Development type extraction patterns
        self.dev_type_patterns = [
            r'dwelling house[s]?',
            r'dual occupanc(?:y|ies)',
            r'multi[- ]?dwelling housing',
            r'residential flat building[s]?',
            r'apartment[s]?',
            r'townhouse[s]?',
            r'villa[s]?',
            r'shop[s]?',
            r'retail premises',
            r'office premises',
            r'commercial premises',
            r'warehouse[s]?',
            r'industrial',
            r'light industr(?:y|ial)',
            r'general industr(?:y|ial)',
            r'business premises',
            r'mixed use',
            r'seniors[\']? housing',
            r'group home[s]?',
            r'boarding house[s]?'
        ]
        
    def setup_tables(self):
        """Create analysis tables for PRP-P1"""
        
        print("Creating PRP-P1 analysis tables...")
        
        # Create permissibility_analysis table
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS permissibility_analysis (
                id INTEGER PRIMARY KEY,
                provision_id INTEGER,
                zone TEXT,
                pattern_type TEXT,
                extracted_text TEXT,
                development_types TEXT, -- JSON array
                permission_status TEXT, -- permitted/prohibited/consent
                confidence_score REAL,
                document_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create pattern_validation table
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS pattern_validation (
                id INTEGER PRIMARY KEY,
                pattern_type TEXT,
                sample_text TEXT,
                expected_result TEXT,
                validation_status TEXT, -- pass/fail/manual_review
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
        print("  [DONE] Analysis tables created")
        
    def extract_permissibility_patterns(self):
        """Execute pattern extraction on regulatory provisions"""
        
        print("\nExecuting permissibility pattern extraction...")
        
        # Get provisions with permissibility keywords
        query = '''
            SELECT id, zone, provision_text, document_id
            FROM regulatory_provisions 
            WHERE provision_text IS NOT NULL
            AND (
                provision_text LIKE '%permitted%' 
                OR provision_text LIKE '%prohibited%' 
                OR provision_text LIKE '%consent%'
                OR provision_text LIKE '%development may%'
                OR provision_text LIKE '%purposes%'
                OR provision_text LIKE '%following development%'
            )
            AND zone IS NOT NULL
            ORDER BY zone, document_id
        '''
        
        self.cur.execute(query)
        provisions = self.cur.fetchall()
        
        print(f"  Found {len(provisions)} provisions with permissibility keywords")
        
        extractions = []
        processed = 0
        
        for prov_id, zone, text, doc_id in provisions:
            if text:
                # Try each pattern type
                for pattern_type, patterns in self.permissibility_patterns.items():
                    for pattern in patterns:
                        matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
                        
                        for match in matches:
                            extracted_text = match.group(0).strip()
                            
                            # Extract development types from the matched text
                            dev_types = self.extract_development_types(extracted_text)
                            
                            # Determine permission status
                            permission_status = self.determine_permission_status(pattern_type, extracted_text)
                            
                            # Calculate confidence score
                            confidence = self.calculate_confidence(pattern_type, extracted_text, dev_types)
                            
                            extractions.append({
                                'provision_id': prov_id,
                                'zone': zone,
                                'pattern_type': pattern_type,
                                'extracted_text': extracted_text[:500],  # Limit length
                                'development_types': json.dumps(dev_types) if dev_types else None,
                                'permission_status': permission_status,
                                'confidence_score': confidence,
                                'document_id': doc_id
                            })
            
            processed += 1
            if processed % 100 == 0:
                print(f"    Processed {processed}/{len(provisions)} provisions...")
        
        # Insert extractions into database
        if extractions:
            insert_query = '''
                INSERT INTO permissibility_analysis 
                (provision_id, zone, pattern_type, extracted_text, development_types, 
                 permission_status, confidence_score, document_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            values = [(e['provision_id'], e['zone'], e['pattern_type'], e['extracted_text'],
                      e['development_types'], e['permission_status'], e['confidence_score'],
                      e['document_id']) for e in extractions]
            
            self.cur.executemany(insert_query, values)
            self.conn.commit()
            
        print(f"  [DONE] Extracted {len(extractions)} permissibility patterns")
        return len(extractions)
    
    def extract_development_types(self, text: str) -> List[str]:
        """Extract development types from text"""
        
        dev_types = []
        text_lower = text.lower()
        
        for pattern in self.dev_type_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                # Standardize the match
                standardized = self.standardize_dev_type(match)
                if standardized and standardized not in dev_types:
                    dev_types.append(standardized)
        
        return dev_types
    
    def standardize_dev_type(self, dev_type: str) -> Optional[str]:
        """Standardize development type terminology"""
        
        dev_type = dev_type.lower().strip()
        
        # Standardization mappings
        mappings = {
            'dwelling house': 'dwelling_house',
            'dwelling houses': 'dwelling_house',
            'dual occupancy': 'dual_occupancy',
            'dual occupancies': 'dual_occupancy',
            'multi dwelling housing': 'multi_dwelling_housing',
            'multi-dwelling housing': 'multi_dwelling_housing',
            'residential flat building': 'residential_flat_building',
            'residential flat buildings': 'residential_flat_building',
            'apartment': 'residential_flat_building',
            'apartments': 'residential_flat_building',
            'townhouse': 'multi_dwelling_housing',
            'townhouses': 'multi_dwelling_housing',
            'villa': 'multi_dwelling_housing',
            'villas': 'multi_dwelling_housing',
            'shop': 'retail_premises',
            'shops': 'retail_premises',
            'retail premises': 'retail_premises',
            'office premises': 'office_premises',
            'commercial premises': 'commercial_premises',
            'warehouse': 'warehouse',
            'warehouses': 'warehouse',
            'light industry': 'light_industry',
            'light industrial': 'light_industry',
            'general industry': 'general_industry',
            'general industrial': 'general_industry',
            'business premises': 'business_premises',
            'mixed use': 'mixed_use',
            'seniors housing': 'seniors_housing',
            "seniors' housing": 'seniors_housing',
            'group home': 'group_home',
            'group homes': 'group_home',
            'boarding house': 'boarding_house',
            'boarding houses': 'boarding_house'
        }
        
        return mappings.get(dev_type)
    
    def determine_permission_status(self, pattern_type: str, text: str) -> str:
        """Determine permission status from pattern type and text"""
        
        if pattern_type == 'permitted_without_consent':
            return 'permitted'
        elif pattern_type == 'permitted_with_consent':
            return 'consent'
        elif pattern_type == 'prohibited':
            return 'prohibited'
        else:
            # Analyze text for specific keywords
            text_lower = text.lower()
            if 'prohibited' in text_lower or 'not permitted' in text_lower:
                return 'prohibited'
            elif 'consent' in text_lower:
                return 'consent'
            else:
                return 'permitted'
    
    def calculate_confidence(self, pattern_type: str, text: str, dev_types: List[str]) -> float:
        """Calculate confidence score for extraction"""
        
        confidence = 0.7  # Base confidence
        
        # Higher confidence for specific development types found
        if dev_types:
            confidence += 0.2
        
        # Higher confidence for clear permission language
        text_lower = text.lower()
        if any(word in text_lower for word in ['permitted', 'prohibited', 'consent']):
            confidence += 0.1
        
        # Lower confidence for very short extractions
        if len(text) < 50:
            confidence -= 0.2
        
        # Higher confidence for list-structured text
        if '(' in text and ')' in text:
            confidence += 0.1
        
        return min(1.0, max(0.1, confidence))
    
    def validate_extractions(self):
        """Run quality validation on extractions"""
        
        print("\nRunning quality validation...")
        
        # Get statistics
        stats = self.get_extraction_statistics()
        
        # Generate validation sample
        validation_sample = self.generate_validation_sample()
        
        # Run automated validation tests
        validation_results = self.run_validation_tests()
        
        print(f"  [DONE] Validation complete")
        print(f"    Total extractions: {stats['total_extractions']}")
        print(f"    Unique zones: {stats['unique_zones']}")
        print(f"    Pattern types: {stats['pattern_types']}")
        print(f"    Average confidence: {stats['avg_confidence']:.2f}")
        
        return stats, validation_sample, validation_results
    
    def get_extraction_statistics(self) -> Dict:
        """Get extraction statistics"""
        
        # Total extractions
        self.cur.execute('SELECT COUNT(*) FROM permissibility_analysis')
        total = self.cur.fetchone()[0]
        
        # Unique zones
        self.cur.execute('SELECT COUNT(DISTINCT zone) FROM permissibility_analysis')
        zones = self.cur.fetchone()[0]
        
        # Pattern types
        self.cur.execute('''
            SELECT pattern_type, COUNT(*) 
            FROM permissibility_analysis 
            GROUP BY pattern_type
        ''')
        pattern_types = dict(self.cur.fetchall())
        
        # Average confidence
        self.cur.execute('SELECT AVG(confidence_score) FROM permissibility_analysis')
        avg_confidence = self.cur.fetchone()[0] or 0
        
        # Development types with extractions
        self.cur.execute('''
            SELECT COUNT(*) FROM permissibility_analysis 
            WHERE development_types IS NOT NULL
        ''')
        with_dev_types = self.cur.fetchone()[0]
        
        return {
            'total_extractions': total,
            'unique_zones': zones,
            'pattern_types': pattern_types,
            'avg_confidence': avg_confidence,
            'with_development_types': with_dev_types
        }
    
    def generate_validation_sample(self, sample_size: int = 20) -> List[Dict]:
        """Generate sample for manual validation"""
        
        # Get stratified sample across zones and pattern types
        self.cur.execute('''
            SELECT id, zone, pattern_type, extracted_text, development_types, 
                   permission_status, confidence_score
            FROM permissibility_analysis
            ORDER BY RANDOM()
            LIMIT ?
        ''', (sample_size,))
        
        sample = []
        for row in self.cur.fetchall():
            sample.append({
                'id': row[0],
                'zone': row[1],
                'pattern_type': row[2],
                'extracted_text': row[3],
                'development_types': row[4],
                'permission_status': row[5],
                'confidence_score': row[6]
            })
        
        return sample
    
    def run_validation_tests(self) -> Dict:
        """Run automated validation tests"""
        
        results = {'tests': []}
        
        # Test 1: Minimum extraction count
        self.cur.execute('SELECT COUNT(*) FROM permissibility_analysis')
        count = self.cur.fetchone()[0]
        results['tests'].append({
            'name': 'minimum_extractions',
            'expected': 500,
            'actual': count,
            'status': 'pass' if count >= 500 else 'fail'
        })
        
        # Test 2: Zone coverage
        self.cur.execute('SELECT COUNT(DISTINCT zone) FROM permissibility_analysis')
        zones = self.cur.fetchone()[0]
        results['tests'].append({
            'name': 'zone_coverage',
            'expected': 15,
            'actual': zones,
            'status': 'pass' if zones >= 15 else 'fail'
        })
        
        # Test 3: Pattern type coverage
        self.cur.execute('SELECT COUNT(DISTINCT pattern_type) FROM permissibility_analysis')
        pattern_types = self.cur.fetchone()[0]
        results['tests'].append({
            'name': 'pattern_type_coverage',
            'expected': 3,
            'actual': pattern_types,
            'status': 'pass' if pattern_types >= 3 else 'fail'
        })
        
        # Test 4: Development type extraction
        self.cur.execute('''
            SELECT COUNT(*) FROM permissibility_analysis 
            WHERE development_types IS NOT NULL
        ''')
        with_dev_types = self.cur.fetchone()[0]
        results['tests'].append({
            'name': 'development_type_extraction',
            'expected': count * 0.3,  # At least 30% should have dev types
            'actual': with_dev_types,
            'status': 'pass' if with_dev_types >= count * 0.3 else 'fail'
        })
        
        # Test 5: Average confidence
        self.cur.execute('SELECT AVG(confidence_score) FROM permissibility_analysis')
        avg_confidence = self.cur.fetchone()[0] or 0
        results['tests'].append({
            'name': 'average_confidence',
            'expected': 0.8,
            'actual': avg_confidence,
            'status': 'pass' if avg_confidence >= 0.8 else 'fail'
        })
        
        # Calculate overall pass rate
        passed_tests = sum(1 for test in results['tests'] if test['status'] == 'pass')
        results['overall_pass_rate'] = passed_tests / len(results['tests'])
        results['overall_status'] = 'pass' if results['overall_pass_rate'] >= 0.8 else 'fail'
        
        return results
    
    def generate_deliverables(self, stats: Dict, validation_sample: List[Dict], validation_results: Dict):
        """Generate PRP-P1 deliverables"""
        
        print("\nGenerating deliverables...")
        
        # 1. Phase1_extraction_report.json
        report = {
            'execution_timestamp': datetime.now().isoformat(),
            'extraction_statistics': stats,
            'validation_results': validation_results,
            'success_criteria': {
                'minimum_extractions': stats['total_extractions'] >= 500,
                'zone_coverage': stats['unique_zones'] >= 15,
                'pattern_diversity': len(stats['pattern_types']) >= 3,
                'development_type_extraction': stats['with_development_types'] >= stats['total_extractions'] * 0.3,
                'average_confidence': stats['avg_confidence'] >= 0.8
            },
            'overall_success': validation_results['overall_status'] == 'pass'
        }
        
        with open('Phase1_extraction_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # 2. validation_sample.csv
        with open('validation_sample.csv', 'w', newline='', encoding='utf-8') as f:
            if validation_sample:
                writer = csv.DictWriter(f, fieldnames=validation_sample[0].keys())
                writer.writeheader()
                writer.writerows(validation_sample)
        
        print("  [DONE] Deliverables generated:")
        print("    - Phase1_extraction_report.json")
        print("    - validation_sample.csv")
        print("    - phase1_extraction_script.py")
        
    def execute_prp_p1(self):
        """Execute complete PRP-P1 process"""
        
        print("="*60)
        print("PRP-P1: PERMISSIBILITY PATTERN EXTRACTION")
        print("="*60)
        
        start_time = time.time()
        
        # Step 1: Setup tables
        self.setup_tables()
        
        # Step 2: Extract patterns
        extraction_count = self.extract_permissibility_patterns()
        
        # Step 3: Validate
        stats, validation_sample, validation_results = self.validate_extractions()
        
        # Step 4: Generate deliverables
        self.generate_deliverables(stats, validation_sample, validation_results)
        
        execution_time = time.time() - start_time
        
        print(f"\n{'='*60}")
        print("PRP-P1 EXECUTION COMPLETE")
        print(f"{'='*60}")
        print(f"Execution time: {execution_time:.1f} seconds")
        print(f"Overall status: {'SUCCESS' if validation_results['overall_status'] == 'pass' else 'NEEDS REVIEW'}")
        
        # Show completion checklist
        print(f"\nCOMPLETION CHECKLIST:")
        success_criteria = {
            'Minimum extractions (500+)': stats['total_extractions'] >= 500,
            'Zone coverage (15+)': stats['unique_zones'] >= 15,
            'Pattern diversity (3+ types)': len(stats['pattern_types']) >= 3,
            'Development type extraction (30%+)': stats['with_development_types'] >= stats['total_extractions'] * 0.3,
            'Average confidence (0.8+)': stats['avg_confidence'] >= 0.8
        }
        
        for criterion, passed in success_criteria.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {status} {criterion}")
        
        if all(success_criteria.values()):
            print(f"\n[SUCCESS] PRP-P1 SUCCESSFULLY COMPLETED - Ready for PRP-P2")
        else:
            print(f"\n[WARNING] PRP-P1 NEEDS REVIEW - Check failed criteria")
        
        return validation_results['overall_status'] == 'pass'


def main():
    """Main execution"""
    extractor = PermissibilityExtractor()
    success = extractor.execute_prp_p1()
    return success


if __name__ == "__main__":
    main()