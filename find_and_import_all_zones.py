import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

class ZoneProvisionImporter:
    """Import all zone-specific provisions from extracted JSON files"""
    
    def __init__(self, db_path: str = 'nsw_planning.db'):
        self.db_path = db_path
        self.zones = ['R1', 'R2', 'R3', 'R4', 'B1', 'B2', 'B4', 'B6', 'IN1', 'IN2', 'E2', 'E3', 'RE1', 'RE2']
        self.development_types = {
            'R1': ['dwelling_house', 'dual_occupancy', 'secondary_dwelling'],
            'R2': ['dwelling_house', 'dual_occupancy', 'multi_dwelling_housing', 'residential_flat_building', 'secondary_dwelling'],
            'R3': ['dwelling_house', 'multi_dwelling_housing', 'residential_flat_building', 'shop_top_housing'],
            'R4': ['residential_flat_building', 'shop_top_housing', 'mixed_use'],
            'B1': ['shop_top_housing', 'commercial_premises', 'office_premises'],
            'B2': ['shop_top_housing', 'commercial_premises', 'office_premises', 'mixed_use'],
            'B4': ['mixed_use', 'commercial_premises', 'shop_top_housing'],
            'B6': ['enterprise_corridor', 'business_premises', 'office_premises'],
            'IN1': ['light_industries', 'warehouse', 'industrial_retail'],
            'IN2': ['light_industries', 'warehouse', 'industrial'],
            'E2': ['environmental_conservation'],
            'E3': ['environmental_management'],
            'RE1': ['public_recreation'],
            'RE2': ['private_recreation']
        }
        self.imported_count = 0
        self.skipped_count = 0
        
    def find_json_sources(self) -> List[Path]:
        """Find all JSON files containing zone provisions"""
        json_files = []
        search_dirs = [
            'output',
            'validated_outputs', 
            'langextract_verified_output',
            'autoschemakg_output_comprehensive',
            'rag_storage'
        ]
        
        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                for root, dirs, files in os.walk(search_dir):
                    for file in files:
                        if file.endswith('.json'):
                            json_files.append(Path(root) / file)
        
        return json_files
    
    def extract_zone_provisions(self, json_path: Path) -> List[Dict]:
        """Extract zone-specific provisions from JSON file"""
        provisions = []
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Handle different JSON structures
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # Try common keys
                items = data.get('provisions', data.get('items', data.get('content', [])))
                if not isinstance(items, list):
                    items = [data]
            else:
                return []
                
            for item in items:
                # Extract text content
                text = None
                if isinstance(item, str):
                    text = item
                elif isinstance(item, dict):
                    text = item.get('provision_text', item.get('text', item.get('content', '')))
                
                if not text:
                    continue
                    
                # Check if it's a zone-related provision
                for zone in self.zones:
                    if f' {zone} ' in text or f'zone {zone}' in text.lower():
                        # Extract development type if mentioned
                        dev_type = self.identify_development_type(text)
                        
                        # Extract setback values
                        setbacks = self.extract_setback_values(text)
                        
                        if setbacks:
                            provision = {
                                'zone': zone,
                                'development_type': dev_type,
                                'text': text,
                                'setbacks': setbacks,
                                'source_file': str(json_path),
                                'document_id': self.extract_document_id(json_path, item)
                            }
                            provisions.append(provision)
                            
        except Exception as e:
            print(f"Error processing {json_path}: {e}")
            
        return provisions
    
    def identify_development_type(self, text: str) -> str:
        """Identify development type from provision text"""
        text_lower = text.lower()
        
        type_mappings = {
            'multi dwelling housing': 'multi_dwelling_housing',
            'multi-dwelling housing': 'multi_dwelling_housing',
            'residential flat building': 'residential_flat_building',
            'dwelling house': 'dwelling_house',
            'dual occupancy': 'dual_occupancy',
            'shop top housing': 'shop_top_housing',
            'mixed use': 'mixed_use',
            'commercial premises': 'commercial_premises',
            'office premises': 'office_premises',
            'light industries': 'light_industries',
            'warehouse': 'warehouse',
            'secondary dwelling': 'secondary_dwelling'
        }
        
        for key, value in type_mappings.items():
            if key in text_lower:
                return value
                
        return 'general'
    
    def extract_setback_values(self, text: str) -> Dict[str, float]:
        """Extract numeric setback values from text"""
        import re
        
        setbacks = {}
        
        # Pattern to find setback values
        patterns = [
            (r'front.*?(\d+(?:\.\d+)?)\s*(?:metres?|m)', 'front'),
            (r'side.*?(\d+(?:\.\d+)?)\s*(?:metres?|m)', 'side'),
            (r'rear.*?(\d+(?:\.\d+)?)\s*(?:metres?|m)', 'rear'),
            (r'(\d+(?:\.\d+)?)\s*(?:metres?|m).*?front', 'front'),
            (r'(\d+(?:\.\d+)?)\s*(?:metres?|m).*?side', 'side'),
            (r'(\d+(?:\.\d+)?)\s*(?:metres?|m).*?rear', 'rear'),
        ]
        
        for pattern, boundary_type in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                if 0.5 <= value <= 50:  # Reasonable setback range
                    setbacks[boundary_type] = value
                    
        return setbacks
    
    def extract_document_id(self, json_path: Path, item: Dict) -> str:
        """Extract document ID from path or item"""
        if isinstance(item, dict) and 'document_id' in item:
            return item['document_id']
            
        # Try to extract from file path
        path_str = str(json_path)
        if 'Marrickville' in path_str:
            return 'Marrickville_DCP_2011'
        elif 'Ashfield' in path_str:
            return 'Ashfield_DCP_2016'
        elif 'Leichhardt' in path_str:
            return 'Leichhardt_DCP_2013'
        elif 'LEP' in path_str:
            return 'Inner_West_LEP_2022'
        elif 'SEPP' in path_str:
            return 'SEPP_Housing_2021'
            
        return 'Unknown_Source'
    
    def import_to_database(self, provisions: List[Dict]) -> Tuple[int, int]:
        """Import provisions to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        imported = 0
        skipped = 0
        
        for prov in provisions:
            # Check if already exists
            existing = cursor.execute('''
                SELECT COUNT(*) FROM regulatory_provisions
                WHERE zone = ? AND development_type = ? 
                AND provision_text LIKE ?
            ''', (prov['zone'], prov['development_type'], f"%{prov['text'][:50]}%")).fetchone()[0]
            
            if existing > 0:
                skipped += 1
                continue
                
            try:
                # Insert main provision
                cursor.execute('''
                    INSERT INTO regulatory_provisions (
                        provision_type, zone, development_type,
                        provision_text, document_id, section_header,
                        domain_classification, prp_k1_enhanced,
                        classification_confidence, cross_contamination_checked,
                        created_at
                    ) VALUES (
                        'control', ?, ?, ?, ?, 'Building setbacks',
                        'RESIDENTIAL_BUILDINGS', 1, 0.9, 1, ?
                    )
                ''', (
                    prov['zone'],
                    prov['development_type'],
                    prov['text'],
                    prov['document_id'],
                    datetime.now().isoformat()
                ))
                
                provision_id = cursor.lastrowid
                
                # Insert quantitative standards
                for boundary_type, value in prov['setbacks'].items():
                    cursor.execute('''
                        INSERT INTO quantitative_standards (
                            provision_id, numeric_value, unit,
                            context, confidence_score
                        ) VALUES (?, ?, 'm', ?, 0.9)
                    ''', (provision_id, value, f'setback_{boundary_type}'))
                
                imported += 1
                
            except sqlite3.IntegrityError as e:
                print(f"Skipped duplicate: {e}")
                skipped += 1
                
        conn.commit()
        conn.close()
        
        return imported, skipped
    
    def run_import(self) -> Dict:
        """Run the complete import process"""
        print("=" * 60)
        print("PRP-K7: Zone Provision Import Pipeline")
        print("=" * 60)
        
        # Find JSON sources
        json_files = self.find_json_sources()
        print(f"Found {len(json_files)} JSON files to process")
        
        # Extract provisions
        all_provisions = []
        for json_file in json_files:
            provisions = self.extract_zone_provisions(json_file)
            if provisions:
                all_provisions.extend(provisions)
                print(f"  [OK] Extracted {len(provisions)} provisions from {json_file.name}")
        
        print(f"\nTotal provisions extracted: {len(all_provisions)}")
        
        # Import to database
        imported, skipped = self.import_to_database(all_provisions)
        
        print(f"\nImport complete:")
        print(f"  [OK] Imported: {imported}")
        print(f"  [SKIP] Skipped: {skipped}")
        
        return {
            'files_processed': len(json_files),
            'provisions_found': len(all_provisions),
            'imported': imported,
            'skipped': skipped
        }

if __name__ == "__main__":
    importer = ZoneProvisionImporter()
    results = importer.run_import()
    print(f"\nFinal Results: {results}")