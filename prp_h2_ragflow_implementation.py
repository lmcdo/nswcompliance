#!/usr/bin/env python3
"""
PRP-H2: RAGFlow Table/Diagram Extraction Module Implementation
Focus on measurements, numerical data, and structured content
Addresses critical gap found in PRP-H1 where 0 measurements were extracted
"""
import os
import json
from db_config import get_connection  # Unified PostgreSQL connection
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

class RAGFlowTableExtractor:
    """RAGFlow-based extraction for tables, diagrams and structured numerical data"""
    
    def __init__(self):
        self.base_path = Path("C:/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine")
        self.db_path = self.base_path / "nsw_planning_data.db"
        self.ragflow_output_path = self.base_path / "ragflow_output"
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Initialize results tracking
        self.results = {
            'measurements_extracted': 0,
            'tables_processed': 0,
            'diagrams_processed': 0,
            'numerical_values_found': 0,
            'errors': [],
            'success_rate': 0.0
        }
        
    def check_ragflow_tables(self) -> List[Dict]:
        """Check for existing RAGFlow table extraction results"""
        ragflow_files = []
        
        if self.ragflow_output_path.exists():
            for file in self.ragflow_output_path.rglob("*.json"):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if self._contains_table_data(data):
                            ragflow_files.append({
                                'file': str(file),
                                'data': data,
                                'type': 'ragflow_table'
                            })
                except Exception as e:
                    self.logger.warning(f"Could not read {file}: {e}")
                    
        return ragflow_files
        
    def _contains_table_data(self, data: Dict) -> bool:
        """Check if JSON contains table-like structured data"""
        if isinstance(data, dict):
            # Look for table indicators
            table_indicators = ['table', 'rows', 'columns', 'cells', 'header']
            return any(indicator in str(data).lower() for indicator in table_indicators)
        return False
        
    def extract_measurements_from_tables(self, table_data: List[Dict]) -> List[Dict]:
        """Extract numerical measurements from table structures"""
        measurements = []
        
        for table_file in table_data:
            try:
                data = table_file['data']
                file_path = table_file['file']
                
                # Extract measurements using pattern matching
                extracted = self._find_numerical_patterns(data, file_path)
                measurements.extend(extracted)
                
                self.results['tables_processed'] += 1
                
            except Exception as e:
                error_msg = f"Error processing table {table_file['file']}: {e}"
                self.logger.error(error_msg)
                self.results['errors'].append(error_msg)
                
        return measurements
        
    def _find_numerical_patterns(self, data: Any, source_file: str) -> List[Dict]:
        """Find numerical patterns in structured data"""
        measurements = []
        text_content = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
        
        # Common measurement patterns
        patterns = [
            r'(\d+(?:\.\d+)?)\s*m(?:etres?)?(?:\s+setback|setback|\s+height|height)?',
            r'(\d+(?:\.\d+)?)\s*(?:metre|meter)s?',
            r'setback[:\s]+(\d+(?:\.\d+)?)\s*m',
            r'height[:\s]+(\d+(?:\.\d+)?)\s*m',
            r'(\d+(?:\.\d+)?)\s*m\s+(?:minimum|maximum|max|min)',
            r'FSR[:\s]+(\d+(?:\.\d+)?)',
            r'floor\s+space\s+ratio[:\s]+(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)%\s*site\s*coverage',
            r'site\s*coverage[:\s]+(\d+(?:\.\d+)?)%'
        ]
        
        for pattern in patterns:
            import re
            matches = re.finditer(pattern, text_content, re.IGNORECASE)
            for match in matches:
                value = match.group(1)
                context = text_content[max(0, match.start()-50):match.end()+50]
                
                measurement = {
                    'value': float(value),
                    'unit': self._determine_unit(match.group(0)),
                    'type': self._determine_measurement_type(context),
                    'context': context.strip(),
                    'source_file': source_file,
                    'extraction_method': 'ragflow_table'
                }
                measurements.append(measurement)
                self.results['measurements_extracted'] += 1
                self.results['numerical_values_found'] += 1
                
        return measurements
        
    def _determine_unit(self, match_text: str) -> str:
        """Determine the unit of measurement"""
        match_lower = match_text.lower()
        if 'm' in match_lower and ('metre' in match_lower or 'meter' in match_lower):
            return 'metres'
        elif 'm' in match_lower:
            return 'metres'
        elif '%' in match_lower:
            return 'percentage'
        elif 'fsr' in match_lower:
            return 'ratio'
        return 'unknown'
        
    def _determine_measurement_type(self, context: str) -> str:
        """Determine what type of measurement this is"""
        context_lower = context.lower()
        
        if any(word in context_lower for word in ['setback', 'boundary', 'distance']):
            return 'setback'
        elif any(word in context_lower for word in ['height', 'storey', 'level']):
            return 'height'
        elif any(word in context_lower for word in ['fsr', 'floor space ratio']):
            return 'fsr'
        elif any(word in context_lower for word in ['coverage', 'site coverage']):
            return 'site_coverage'
        elif any(word in context_lower for word in ['area', 'size']):
            return 'area'
        else:
            return 'general'
            
    def store_measurements_to_database(self, measurements: List[Dict]):
        """Store extracted measurements to database"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Create measurements table if not exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ragflow_measurements (
                    id SERIAL PRIMARY KEY SERIAL,
                    value REAL,
                    unit TEXT,
                    measurement_type TEXT,
                    context TEXT,
                    source_file TEXT,
                    extraction_method TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert measurements
            for measurement in measurements:
                cursor.execute('''
                    INSERT INTO ragflow_measurements 
                    (value, unit, measurement_type, context, source_file, extraction_method)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    measurement['value'],
                    measurement['unit'],
                    measurement['type'],
                    measurement['context'],
                    measurement['source_file'],
                    measurement['extraction_method']
                ))
                
            conn.commit()
            conn.close()
            
            self.logger.info(f"Stored {len(measurements)} measurements to database")
            
        except Exception as e:
            error_msg = f"Database storage error: {e}"
            self.logger.error(error_msg)
            self.results['errors'].append(error_msg)
            
    def process_mineru_output(self) -> List[Dict]:
        """Process MinerU output for table data"""
        measurements = []
        mineru_paths = [
            self.base_path / "output",
            self.base_path / "output_sepps"
        ]
        
        for mineru_path in mineru_paths:
            if mineru_path.exists():
                for json_file in mineru_path.rglob("*.json"):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            
                        # Extract from MinerU structure
                        extracted = self._extract_from_mineru_structure(data, str(json_file))
                        measurements.extend(extracted)
                        
                    except Exception as e:
                        self.logger.warning(f"Could not process MinerU file {json_file}: {e}")
                        
        return measurements
        
    def _extract_from_mineru_structure(self, data: Dict, source_file: str) -> List[Dict]:
        """Extract measurements from MinerU JSON structure"""
        measurements = []
        
        # MinerU typically has 'content' or 'text' fields
        text_content = ""
        if isinstance(data, dict):
            if 'content' in data:
                text_content = str(data['content'])
            elif 'text' in data:
                text_content = str(data['text'])
            else:
                text_content = json.dumps(data)
        else:
            text_content = str(data)
            
        # Use same pattern matching as table extraction
        extracted = self._find_numerical_patterns(text_content, source_file)
        measurements.extend(extracted)
        
        return measurements
        
    def run_complete_extraction(self) -> Dict:
        """Run complete RAGFlow table extraction pipeline"""
        print("=" * 60)
        print("PRP-H2: RAGFLOW TABLE/DIAGRAM EXTRACTION MODULE")
        print("=" * 60)
        print("Targeting measurements and numerical data missed by PRP-H1")
        print()
        
        start_time = time.time()
        all_measurements = []
        
        # Step 1: Check RAGFlow tables
        print("Step 1: Checking RAGFlow table outputs...")
        ragflow_tables = self.check_ragflow_tables()
        print(f"Found {len(ragflow_tables)} RAGFlow table files")
        
        if ragflow_tables:
            table_measurements = self.extract_measurements_from_tables(ragflow_tables)
            all_measurements.extend(table_measurements)
            print(f"Extracted {len(table_measurements)} measurements from tables")
        
        # Step 2: Process MinerU output
        print("\nStep 2: Processing MinerU structured output...")
        mineru_measurements = self.process_mineru_output()
        all_measurements.extend(mineru_measurements)
        print(f"Extracted {len(mineru_measurements)} measurements from MinerU output")
        
        # Step 3: Store to database
        print("\nStep 3: Storing measurements to database...")
        if all_measurements:
            self.store_measurements_to_database(all_measurements)
        
        # Calculate final results
        execution_time = time.time() - start_time
        total_extracted = len(all_measurements)
        
        self.results.update({
            'total_measurements_extracted': total_extracted,
            'execution_time_seconds': execution_time,
            'success_rate': (total_extracted / max(1, total_extracted + len(self.results['errors']))) * 100
        })
        
        # Print results
        print("\n" + "=" * 60)
        print("PRP-H2 EXTRACTION RESULTS:")
        print("=" * 60)
        print(f"Total measurements extracted: {total_extracted}")
        print(f"Tables processed: {self.results['tables_processed']}")
        print(f"Numerical values found: {self.results['numerical_values_found']}")
        print(f"Execution time: {execution_time:.2f} seconds")
        print(f"Success rate: {self.results['success_rate']:.1f}%")
        
        if self.results['errors']:
            print(f"Errors encountered: {len(self.results['errors'])}")
            for error in self.results['errors'][:3]:  # Show first 3 errors
                print(f"  - {error}")
                
        # Critical assessment
        print("\nCRITICAL ASSESSMENT:")
        if total_extracted >= 25:
            print("✅ SUCCESS: Extracted sufficient measurements")
        elif total_extracted >= 10:
            print("⚠️  PARTIAL: Some measurements found, needs optimization")
        else:
            print("❌ CRITICAL: Insufficient measurements - need different approach")
            
        return self.results

def main():
    """Execute PRP-H2 RAGFlow extraction"""
    extractor = RAGFlowTableExtractor()
    results = extractor.run_complete_extraction()
    
    # Save results to file
    results_file = Path("PRP_H2_RESULTS.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nDetailed results saved to: {results_file}")

if __name__ == "__main__":
    main()