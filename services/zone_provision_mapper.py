#!/usr/bin/env python3
"""
Zone-Provision Mapper for PRP-8B
Maps regulatory provisions to zones using zone table data and content analysis
"""

import psycopg2
import re
import json
from typing import Dict, List, Set
from datetime import datetime
from .db_config import get_connection

class ZoneProvisionMapper:
    """Maps regulatory provisions to appropriate zones"""

    def __init__(self):
        self.conn = get_connection()
        
        # Available zones from zone tables
        self.available_zones = ['B1', 'B2', 'B4', 'R1', 'R2', 'R3', 'R4']
        
        # Zone mapping statistics
        self.mapping_stats = {
            'total_provisions': 0,
            'mapped_provisions': 0,
            'zone_distribution': {},
            'mapping_methods': {}
        }
    
    def analyze_and_map_zones(self):
        """Analyze regulatory provisions and map them to zones"""
        
        print("=== Zone-Provision Mapping Analysis ===")
        print(f"Available zones: {self.available_zones}")
        
        with self.conn.cursor() as cur:
            # Get total provision count
            cur.execute("SELECT COUNT(*) FROM regulatory_provisions")
            self.mapping_stats['total_provisions'] = cur.fetchone()[0]
            print(f"Total provisions to analyze: {self.mapping_stats['total_provisions']}")
            
            # Get zone table data for content matching
            zone_documents = self.get_zone_document_mapping()
            print(f"Zone documents found: {len(zone_documents)} entries")
            
            # Method 1: Direct document source matching
            print("\n--- Method 1: Document Source Matching ---")
            mapped_by_document = self.map_by_document_source(zone_documents)
            
            # Method 2: Content analysis for zone references  
            print("\n--- Method 2: Content Analysis ---")
            mapped_by_content = self.map_by_content_analysis()
            
            # Method 3: Council and development type inference
            print("\n--- Method 3: Council/Development Type Inference ---")
            mapped_by_inference = self.map_by_council_inference()
            
            # Combine mappings with priority order
            final_mappings = self.combine_mappings(
                mapped_by_document, 
                mapped_by_content, 
                mapped_by_inference
            )
            
            # Update database with zone mappings
            print("\n--- Updating Database ---")
            self.update_provision_zones(final_mappings)
            
            # Generate mapping report
            self.generate_mapping_report()
    
    def get_zone_document_mapping(self) -> Dict[str, List[str]]:
        """Get zone-to-document mappings from zone tables"""
        
        zone_docs = {}
        
        with self.conn.cursor() as cur:
            # Get source documents from zone tables
            cur.execute("""
                SELECT DISTINCT zone, source_document, source_file 
                FROM zone_setback_rules 
                WHERE source_document IS NOT NULL
                UNION
                SELECT DISTINCT zone, source_document, source_file 
                FROM zone_setback_rules_comprehensive_archived
                WHERE source_document IS NOT NULL
            """)
            
            for zone, doc, file_path in cur.fetchall():
                if zone not in zone_docs:
                    zone_docs[zone] = []
                
                if doc:
                    zone_docs[zone].append(doc.lower())
                if file_path:
                    zone_docs[zone].append(file_path.lower())
        
        return zone_docs
    
    def map_by_document_source(self, zone_documents: Dict[str, List[str]]) -> Dict[int, str]:
        """Map provisions to zones based on document source matching"""
        
        mappings = {}
        
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT id, document_id, section_header, provision_text
                FROM regulatory_provisions 
                WHERE zone IS NULL
                ORDER BY id
            """)
            
            provisions = cur.fetchall()
            
            for prov_id, doc_id, section_header, text in provisions:
                # Check against zone documents
                for zone, zone_docs in zone_documents.items():
                    matched = False
                    
                    # Check document ID (as string)
                    if doc_id:
                        doc_str = str(doc_id).lower()
                        if any(zone_doc in doc_str for zone_doc in zone_docs):
                            mappings[prov_id] = zone
                            matched = True
                            break
                    
                    # Check section header
                    if not matched and section_header:
                        header_lower = section_header.lower()
                        if any(zone_doc in header_lower for zone_doc in zone_docs):
                            mappings[prov_id] = zone
                            matched = True
                            break
                    
                    if matched:
                        break
        
        print(f"Document source mapping: {len(mappings)} provisions mapped")
        self.mapping_stats['mapping_methods']['document_source'] = len(mappings)
        
        return mappings
    
    def map_by_content_analysis(self) -> Dict[int, str]:
        """Map provisions to zones based on content analysis"""
        
        mappings = {}
        
        # Zone reference patterns
        zone_patterns = {
            'R1': [r'\bR1\b', r'General Residential', r'general residential'],
            'R2': [r'\bR2\b', r'Low Density Residential', r'low density residential'],
            'R3': [r'\bR3\b', r'Medium Density Residential', r'medium density residential'], 
            'R4': [r'\bR4\b', r'High Density Residential', r'high density residential'],
            'B1': [r'\bB1\b', r'Neighbourhood Centre', r'neighbourhood centre'],
            'B2': [r'\bB2\b', r'Local Centre', r'local centre'],
            'B4': [r'\bB4\b', r'Mixed Use', r'mixed use']
        }
        
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT id, provision_text, development_type
                FROM regulatory_provisions 
                WHERE zone IS NULL 
                AND provision_text IS NOT NULL
                ORDER BY id
            """)
            
            provisions = cur.fetchall()
            
            for prov_id, text, dev_type in provisions:
                if not text:
                    continue
                
                text_lower = text.lower()
                
                # Check for explicit zone references
                for zone, patterns in zone_patterns.items():
                    for pattern in patterns:
                        if re.search(pattern, text_lower):
                            mappings[prov_id] = zone
                            break
                    
                    if prov_id in mappings:
                        break
        
        print(f"Content analysis mapping: {len(mappings)} provisions mapped")
        self.mapping_stats['mapping_methods']['content_analysis'] = len(mappings)
        
        return mappings
    
    def map_by_council_inference(self) -> Dict[int, str]:
        """Map provisions to zones based on council and development type patterns"""
        
        mappings = {}
        
        # Development type to likely zone mapping
        dev_type_zones = {
            'dwelling_house': ['R1', 'R2', 'R3'],
            'dual_occupancy': ['R2', 'R3'],
            'multi_dwelling_housing': ['R3', 'R4'], 
            'residential_flat_building': ['R3', 'R4'],
            'shop': ['B1', 'B2'],
            'office_premises': ['B2', 'B4'],
            'mixed_use_development': ['B4'],
            'commercial': ['B1', 'B2', 'B4']
        }
        
        with self.conn.cursor() as cur:
            # Get provisions without zones but with development types
            cur.execute("""
                SELECT id, development_type, section_header, provision_text
                FROM regulatory_provisions 
                WHERE zone IS NULL 
                AND development_type IS NOT NULL
                ORDER BY id
            """)
            
            provisions = cur.fetchall()
            
            for prov_id, dev_type, section_header, text in provisions:
                if dev_type and dev_type.lower() in dev_type_zones:
                    # Use most common zone for this development type
                    likely_zones = dev_type_zones[dev_type.lower()]
                    mappings[prov_id] = likely_zones[0]  # Take first/most likely
        
        print(f"Council inference mapping: {len(mappings)} provisions mapped")
        self.mapping_stats['mapping_methods']['council_inference'] = len(mappings)
        
        return mappings
    
    def combine_mappings(self, *mapping_dicts) -> Dict[int, str]:
        """Combine multiple mapping dictionaries with priority order"""
        
        final_mappings = {}
        
        # Priority order: document source > content analysis > inference
        for mapping_dict in mapping_dicts:
            for prov_id, zone in mapping_dict.items():
                if prov_id not in final_mappings:
                    final_mappings[prov_id] = zone
        
        print(f"Combined mappings: {len(final_mappings)} total provisions mapped")
        
        return final_mappings
    
    def update_provision_zones(self, mappings: Dict[int, str]):
        """Update regulatory provisions with zone mappings"""
        
        if not mappings:
            print("No zone mappings to update")
            return
        
        with self.conn.cursor() as cur:
            # Batch update zones
            zone_updates = []
            for prov_id, zone in mappings.items():
                zone_updates.append((zone, prov_id))
            
            print(f"Updating {len(zone_updates)} provisions with zone assignments...")
            
            cur.executemany(
                "UPDATE regulatory_provisions SET zone = %s WHERE id = %s",
                zone_updates
            )
            
            self.conn.commit()
            print(f"Updated {cur.rowcount} provisions with zones")
            
            self.mapping_stats['mapped_provisions'] = len(zone_updates)
            
            # Update zone distribution stats
            for zone in mappings.values():
                self.mapping_stats['zone_distribution'][zone] = \
                    self.mapping_stats['zone_distribution'].get(zone, 0) + 1
    
    def generate_mapping_report(self):
        """Generate comprehensive mapping report"""
        
        report = [
            "=" * 60,
            "ZONE-PROVISION MAPPING REPORT", 
            "=" * 60,
            f"Generated: {datetime.now().isoformat()}",
            "",
            "MAPPING RESULTS",
            "-" * 30,
            f"Total provisions: {self.mapping_stats['total_provisions']:,}",
            f"Mapped provisions: {self.mapping_stats['mapped_provisions']:,}",
            f"Unmapped provisions: {self.mapping_stats['total_provisions'] - self.mapping_stats['mapped_provisions']:,}",
            f"Mapping rate: {(self.mapping_stats['mapped_provisions'] / self.mapping_stats['total_provisions'] * 100):.1f}%",
            "",
            "ZONE DISTRIBUTION",
            "-" * 30
        ]
        
        for zone in sorted(self.mapping_stats['zone_distribution'].keys()):
            count = self.mapping_stats['zone_distribution'][zone]
            report.append(f"{zone}: {count:,} provisions")
        
        report.extend([
            "",
            "MAPPING METHODS",
            "-" * 30
        ])
        
        for method, count in self.mapping_stats['mapping_methods'].items():
            report.append(f"{method}: {count:,} provisions")
        
        report.extend([
            "",
            "NEXT STEPS",
            "-" * 30,
            "1. Review mapping accuracy with sample provisions",
            "2. Run authoritative migration with updated zone data",
            "3. Validate tier classifications",
            "4. Test API integration with zone-aware provisions"
        ])
        
        report_text = "\n".join(report)
        print("\n" + report_text)
        
        # Save report
        try:
            with open('ZONE_MAPPING_REPORT.txt', 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"\nReport saved to: ZONE_MAPPING_REPORT.txt")
        except Exception as e:
            print(f"Could not save report: {e}")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

def main():
    """Main execution"""
    
    print("Starting Zone-Provision Mapping for PRP-8B")
    print("=" * 50)
    
    mapper = ZoneProvisionMapper()
    
    try:
        mapper.analyze_and_map_zones()
        print("\nZone mapping completed successfully!")
        
    except Exception as e:
        print(f"Error during zone mapping: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        mapper.close()

if __name__ == "__main__":
    main()