#!/usr/bin/env python3
"""
Comprehensive analysis of zone data across all output folders
"""

import json
import os
from pathlib import Path
import re
from collections import defaultdict, Counter

class ZoneDataAnalyzer:
    """Analyze zone data across all extraction outputs"""
    
    def __init__(self):
        self.zone_data = defaultdict(list)
        self.stats = {
            'files_processed': 0,
            'files_with_zones': 0,
            'total_zone_references': 0,
            'unique_zones': set(),
            'zone_provision_mappings': []
        }
        
        # Zone patterns to look for
        self.zone_patterns = [
            r'R[1-4]\s*[-–]\s*[A-Za-z\s]+(?:Residential|residential)',
            r'B[1-4]\s*[-–]\s*[A-Za-z\s]+(?:Zone|zone|Centre|centre)',
            r'RE[1-2]\s*[-–]\s*[A-Za-z\s]+',
            r'SP[1-3]\s*[-–]\s*[A-Za-z\s]+',
            r'E[1-4]\s*[-–]\s*[A-Za-z\s]+',
            r'IN[1-3]\s*[-–]\s*[A-Za-z\s]+',
            r'C[1-9]\s*[-–]\s*[A-Za-z\s]+',
        ]
    
    def analyze_all_outputs(self):
        """Analyze zone data in all output directories"""
        
        print("COMPREHENSIVE ZONE DATA ANALYSIS")
        print("=" * 50)
        
        # Directories to analyze
        output_dirs = [
            'autoschemakg_output_ollama_final',
            'langextract_verified_output', 
            'output',
            'monitored_pipeline_output',
            'validated_outputs'
        ]
        
        for output_dir in output_dirs:
            if os.path.exists(output_dir):
                print(f"\n--- Analyzing {output_dir} ---")
                self.analyze_directory(output_dir)
            else:
                print(f"Directory not found: {output_dir}")
        
        # Generate comprehensive report
        self.generate_zone_analysis_report()
        
        return self.stats
    
    def analyze_directory(self, directory):
        """Analyze all JSON files in a directory"""
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(root, file)
                    self.analyze_json_file(file_path)
    
    def analyze_json_file(self, file_path):
        """Analyze a single JSON file for zone data"""
        
        try:
            self.stats['files_processed'] += 1
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Look for zone patterns in the raw content first
            zones_found = []
            for pattern in self.zone_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                zones_found.extend(matches)
            
            if zones_found:
                self.stats['files_with_zones'] += 1
                self.stats['total_zone_references'] += len(zones_found)
                
                # Clean up zone names
                clean_zones = []
                for zone in zones_found:
                    clean_zone = self.clean_zone_name(zone)
                    if clean_zone:
                        clean_zones.append(clean_zone)
                        self.stats['unique_zones'].add(clean_zone)
                
                if clean_zones:
                    self.zone_data[file_path] = clean_zones
                    print(f"    {os.path.basename(file_path)}: {len(clean_zones)} zones")
            
            # Try to parse as JSON for structured analysis
            try:
                data = json.loads(content)
                self.analyze_structured_json(data, file_path)
            except json.JSONDecodeError:
                # Try JSONL format
                try:
                    for line_num, line in enumerate(content.split('\n')):
                        if line.strip():
                            line_data = json.loads(line)
                            self.analyze_structured_json(line_data, f"{file_path}:line{line_num}")
                except json.JSONDecodeError:
                    pass  # Not valid JSON, but we already did text analysis
                    
        except Exception as e:
            print(f"    Error analyzing {file_path}: {e}")
    
    def analyze_structured_json(self, data, source):
        """Analyze structured JSON data for zone-provision mappings"""
        
        if isinstance(data, dict):
            # Check for AutoSchemaKG format
            if 'original_text' in data and 'entity_relation_dict' in data:
                self.extract_autoschemakg_zones(data, source)
            
            # Check for LangExtract format
            elif 'verified_provisions' in data:
                self.extract_langextract_zones(data, source)
            
            # Recursive check for nested structures
            for value in data.values():
                if isinstance(value, (dict, list)):
                    self.analyze_structured_json(value, source)
                    
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self.analyze_structured_json(item, source)
    
    def extract_autoschemakg_zones(self, data, source):
        """Extract zone data from AutoSchemaKG format"""
        
        text = data.get('original_text', '')
        
        # Look for zone-specific provisions
        zone_provisions = []
        
        # Parse entity relations for zone mappings
        entity_relations = data.get('entity_relation_dict', [])
        event_entities = data.get('event_entity_relation_dict', [])
        
        for event in event_entities:
            event_text = event.get('Event', '')
            entities = event.get('Entity', [])
            
            # Look for zone mentions in events
            for zone_pattern in self.zone_patterns:
                zone_matches = re.findall(zone_pattern, event_text, re.IGNORECASE)
                for zone_match in zone_matches:
                    clean_zone = self.clean_zone_name(zone_match)
                    if clean_zone:
                        zone_provisions.append({
                            'zone': clean_zone,
                            'provision_text': event_text,
                            'source': source,
                            'entities': entities
                        })
        
        if zone_provisions:
            self.stats['zone_provision_mappings'].extend(zone_provisions)
            print(f"    AutoSchemaKG: {len(zone_provisions)} zone-provision mappings")
    
    def extract_langextract_zones(self, data, source):
        """Extract zone data from LangExtract format"""
        
        provisions = data.get('verified_provisions', [])
        
        for provision in provisions:
            text = provision.get('regulatory_text', '') + ' ' + provision.get('applies_to', '')
            
            # Look for zone references
            for zone_pattern in self.zone_patterns:
                zone_matches = re.findall(zone_pattern, text, re.IGNORECASE)
                for zone_match in zone_matches:
                    clean_zone = self.clean_zone_name(zone_match)
                    if clean_zone:
                        self.stats['zone_provision_mappings'].append({
                            'zone': clean_zone,
                            'provision_text': text,
                            'source': source,
                            'clause_reference': provision.get('clause_reference'),
                            'provision_type': provision.get('provision_type')
                        })
    
    def clean_zone_name(self, zone_text):
        """Clean and standardize zone names"""
        
        # Common zone mappings
        zone_mappings = {
            'R1': 'R1',
            'R2': 'R2', 
            'R3': 'R3',
            'R4': 'R4',
            'B1': 'B1',
            'B2': 'B2',
            'B3': 'B3',
            'B4': 'B4',
            'RE1': 'RE1',
            'RE2': 'RE2',
            'SP1': 'SP1',
            'SP2': 'SP2',
            'SP3': 'SP3',
            'E1': 'E1',
            'E2': 'E2',
            'E3': 'E3',
            'E4': 'E4',
            'IN1': 'IN1',
            'IN2': 'IN2',
            'IN3': 'IN3',
        }
        
        # Extract zone code
        zone_match = re.search(r'([A-Z]+[0-9]+)', zone_text.upper())
        if zone_match:
            zone_code = zone_match.group(1)
            return zone_mappings.get(zone_code, zone_code)
        
        return None
    
    def generate_zone_analysis_report(self):
        """Generate comprehensive zone analysis report"""
        
        print(f"\n" + "=" * 50)
        print("ZONE DATA ANALYSIS REPORT")
        print("=" * 50)
        
        print(f"Files processed: {self.stats['files_processed']}")
        print(f"Files with zone data: {self.stats['files_with_zones']}")
        print(f"Total zone references: {self.stats['total_zone_references']}")
        print(f"Unique zones found: {len(self.stats['unique_zones'])}")
        print(f"Zone-provision mappings: {len(self.stats['zone_provision_mappings'])}")
        
        if self.stats['unique_zones']:
            print(f"\nUnique zones identified:")
            for zone in sorted(self.stats['unique_zones']):
                print(f"  {zone}")
        
        # Zone coverage by type
        zone_types = defaultdict(int)
        for zone in self.stats['unique_zones']:
            zone_type = re.match(r'([A-Z]+)', zone)
            if zone_type:
                zone_types[zone_type.group(1)] += 1
        
        if zone_types:
            print(f"\nZone coverage by type:")
            for zone_type, count in sorted(zone_types.items()):
                print(f"  {zone_type}: {count} zones")
        
        # Sample zone-provision mappings
        if self.stats['zone_provision_mappings']:
            print(f"\nSample zone-provision mappings:")
            for i, mapping in enumerate(self.stats['zone_provision_mappings'][:5]):
                print(f"  {i+1}. Zone {mapping['zone']}: {mapping['provision_text'][:100]}...")
        
        # Files with most zone data
        zone_counts = {file: len(zones) for file, zones in self.zone_data.items()}
        top_files = sorted(zone_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        if top_files:
            print(f"\nFiles with most zone data:")
            for file_path, count in top_files:
                print(f"  {os.path.basename(file_path)}: {count} zones")
        
        # Assessment
        print(f"\n" + "=" * 50)
        print("ASSESSMENT")
        print("=" * 50)
        
        if len(self.stats['zone_provision_mappings']) > 1000:
            print("🎉 EXCELLENT: Found extensive zone-provision mappings!")
            print("   Recommendation: Use this data to dramatically improve zone coverage")
        elif len(self.stats['zone_provision_mappings']) > 100:
            print("✅ GOOD: Found significant zone-provision data")
            print("   Recommendation: Extract and integrate this zone data")
        elif len(self.stats['zone_provision_mappings']) > 10:
            print("⚠️ LIMITED: Found some zone data but coverage is low")
            print("   Recommendation: May need additional zone mapping strategies")
        else:
            print("❌ POOR: Very limited zone data found")
            print("   Recommendation: Need alternative approaches to zone assignment")
        
        # Save detailed report
        report = {
            'analysis_timestamp': str(os.path.getctime('.')),
            'statistics': dict(self.stats),
            'unique_zones': list(self.stats['unique_zones']),
            'zone_provision_mappings': self.stats['zone_provision_mappings'],
            'top_files': dict(top_files)
        }
        
        # Convert sets to lists for JSON serialization
        report['statistics']['unique_zones'] = list(report['statistics']['unique_zones'])
        
        try:
            with open('COMPREHENSIVE_ZONE_ANALYSIS.json', 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"\nDetailed analysis saved: COMPREHENSIVE_ZONE_ANALYSIS.json")
        except Exception as e:
            print(f"Could not save detailed report: {e}")
        
        return report

def main():
    """Execute comprehensive zone analysis"""
    
    analyzer = ZoneDataAnalyzer()
    results = analyzer.analyze_all_outputs()
    
    # Return True if we found significant zone data
    return len(results['zone_provision_mappings']) > 100

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)