#!/usr/bin/env python3
"""
PRP-8B CHUNK 3: HierarchyResolver CLI
Command line interface for the HierarchyResolver service
"""

import argparse
import json
import sys
from hierarchy_resolver import HierarchyResolver

def main():
    parser = argparse.ArgumentParser(description='PRP-8B Hierarchy Resolution CLI')
    parser.add_argument('--zone', required=True, help='Zone code (e.g., R2)')
    parser.add_argument('--property-id', type=int, help='Property ID')
    parser.add_argument('--development-type', help='Development type')
    parser.add_argument('--format', choices=['json', 'summary'], default='json', help='Output format')
    
    args = parser.parse_args()
    
    resolver = HierarchyResolver()
    
    try:
        # Resolve hierarchy
        result = resolver.resolve_hierarchy(
            zone_code=args.zone,
            property_id=args.property_id,
            development_type=args.development_type
        )
        
        if args.format == 'json':
            # Output JSON for API consumption
            print(json.dumps(result, indent=2))
        else:
            # Output summary for human consumption
            print(f"Zone: {args.zone}")
            print(f"Total provisions found: {result['processing_metadata']['total_provisions_found']}")
            print(f"Primary authorities: {len(result['primary_authorities'])}")
            print(f"Complexity: {result['complexity_assessment']}")
            print(f"Confidence: {result['confidence_level']:.2f}")
            print(f"Tier distribution: {result['processing_metadata']['tier_distribution']}")
            print(f"Cache hit: {result['processing_metadata'].get('cache_hit', False)}")
            
    except Exception as e:
        error_result = {
            "error": str(e),
            "zone_code": args.zone,
            "property_id": args.property_id,
            "development_type": args.development_type,
            "success": False
        }
        
        if args.format == 'json':
            print(json.dumps(error_result, indent=2))
        else:
            print(f"ERROR: {e}")
            
        sys.exit(1)
        
    finally:
        resolver.close()

if __name__ == "__main__":
    main()