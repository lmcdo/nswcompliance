#!/usr/bin/env python3
"""
Extract addresses from LightRAG entity data that's already processed
"""
import json
import re
from pathlib import Path

def extract_addresses_from_entities():
    """Extract street addresses from LightRAG entity files"""
    
    # Street patterns and address indicators
    street_suffixes = ['Street', 'St', 'Road', 'Rd', 'Avenue', 'Ave', 'Lane', 'Parade', 
                      'Place', 'Pl', 'Drive', 'Dr', 'Circuit', 'Crt', 'Crescent', 'Cres']
    
    addresses = {
        'ashfield': set(),
        'leichhardt': set(), 
        'marrickville': set()
    }
    
    # Process each area's LightRAG entities
    for area in ['ashfield', 'leichhardt', 'marrickville']:
        storage_dir = Path(f"lightrag_{area}_storage")
        entities_file = storage_dir / "kv_store_full_entities.json"
        
        if not entities_file.exists():
            print(f"No entities file found for {area}")
            continue
            
        try:
            with open(entities_file, 'r', encoding='utf-8') as f:
                entities_data = json.load(f)
            
            print(f"Processing {len(entities_data)} documents for {area}")
            
            # Extract all entity names
            all_entities = set()
            for doc_id, doc_data in entities_data.items():
                if 'entity_names' in doc_data:
                    all_entities.update(doc_data['entity_names'])
            
            print(f"Found {len(all_entities)} unique entities for {area}")
            
            # Find street names and addresses
            for entity in all_entities:
                entity = entity.strip()
                
                # Look for street names
                for suffix in street_suffixes:
                    if entity.endswith(' ' + suffix) or entity.endswith(' ' + suffix.lower()):
                        # Clean up the street name
                        street_name = entity.replace(' Sub Area', '').replace(' Distinctive Neighbourhood', '')
                        if len(street_name) > 3 and not any(x in street_name.lower() for x in ['area', 'zone', 'development', 'council', 'plan']):
                            addresses[area].add(street_name)
                
                # Look for numbered addresses (basic pattern)
                addr_pattern = r'^\d+[A-Za-z]?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Street|St|Road|Rd|Avenue|Ave|Lane|Parade|Place|Pl|Drive|Dr)$'
                if re.match(addr_pattern, entity):
                    addresses[area].add(entity)
            
            print(f"Extracted {len(addresses[area])} addresses/streets for {area}")
            
        except Exception as e:
            print(f"Error processing {area}: {e}")
    
    # Combine and save results
    all_addresses = []
    for area, area_addresses in addresses.items():
        for addr in sorted(area_addresses):
            all_addresses.append({
                'address': addr,
                'area': area.capitalize(),
                'type': 'numbered_address' if re.match(r'^\d+', addr) else 'street_name'
            })
    
    # Save address database
    output_file = Path("public/regulatory-data/inner_west_addresses.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    address_data = {
        "extraction_date": "2025-01-25",
        "extraction_method": "LightRAG entity analysis", 
        "total_addresses": len(all_addresses),
        "areas_covered": ["Ashfield", "Leichhardt", "Marrickville"],
        "addresses": all_addresses,
        "summary": {
            "ashfield": len(addresses['ashfield']),
            "leichhardt": len(addresses['leichhardt']),
            "marrickville": len(addresses['marrickville'])
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(address_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n+ Saved {len(all_addresses)} addresses to {output_file}")
    
    # Show sample addresses
    print("\nSample addresses found:")
    for area in ['ashfield', 'leichhardt', 'marrickville']:
        print(f"\n{area.capitalize()}:")
        sample = sorted(list(addresses[area]))[:10]
        for addr in sample:
            print(f"  {addr}")
    
    return address_data

if __name__ == "__main__":
    print("Inner West Address Extraction")
    print("=" * 50)
    addresses = extract_addresses_from_entities()
    print(f"\nTotal addresses extracted: {addresses['total_addresses']}")