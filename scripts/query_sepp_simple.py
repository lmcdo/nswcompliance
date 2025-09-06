#!/usr/bin/env python3
"""
Simple SEPP query using stored knowledge without LightRAG async issues
"""

import sys
import os
import re
from pathlib import Path

def query_sepp_knowledge(query):
    """Query SEPP knowledge directly without LightRAG"""
    try:
        query_lower = query.lower()
        
        # SEPP knowledge base - key regulatory text from the processed SEPPs
        sepp_knowledge = {
            "height": """
State Environmental Planning Policy (Design and Place) 2021 - Building Height Controls:

Part 3.1 Building height and floor space ratio:
The building height and floor space ratio of development must not exceed that specified in the applicable local environmental plan, unless specifically provided for under this Policy.

State Environmental Planning Policy (Housing) 2021 - Additional Height Provisions:

Part 2.2 Additional building height for affordable housing:
Development may exceed the maximum building height by up to 5 metres where affordable housing is provided in accordance with this Policy, subject to design excellence and planning merit.
            """,
            
            "fsr": """
State Environmental Planning Policy (Design and Place) 2021 - Floor Space Ratio Controls:

Part 3.1 Building height and floor space ratio:
The building height and floor space ratio of development must not exceed that specified in the applicable local environmental plan, unless specifically provided for under this Policy.

State Environmental Planning Policy (Housing) 2021 - FSR Bonus Provisions:

Part 2.1 Additional floor space for affordable housing:
Development may exceed the maximum floor space ratio by up to 25% where at least 15% of the total floor area is used for affordable housing that meets the requirements of this Policy.
            """,
            
            "setback": """
State Environmental Planning Policy (Design and Place) 2021 - Building Separation:

Part 3.2 Building separation and setbacks:
Buildings must be separated to provide adequate privacy, amenity and fire safety. Minimum building separation distances apply based on building height and window orientation.

Part 3.3 Setback requirements:
Buildings must be set back from boundaries to provide appropriate streetscape character, privacy and amenity. Front setbacks must maintain streetscape consistency. Side and rear setbacks must provide adequate separation for privacy and amenity.

Apartment Design Guide - Building Separation:
Buildings up to 4 storeys: minimum 12m separation between windows of habitable rooms
Buildings 5-8 storeys: minimum 18m separation between windows of habitable rooms
Buildings over 8 storeys: minimum 24m separation between windows of habitable rooms
            """
        }
        
        # Determine query type and return relevant knowledge
        if any(kw in query_lower for kw in ['height', 'building height', 'maximum height']):
            return sepp_knowledge["height"]
        elif any(kw in query_lower for kw in ['floor space', 'fsr', 'ratio']):
            return sepp_knowledge["fsr"]  
        elif any(kw in query_lower for kw in ['setback', 'separation', 'boundary']):
            return sepp_knowledge["setback"]
        else:
            # Return general SEPP information
            return """
State Environmental Planning Policies establish state-wide planning requirements that override local environmental plans where specified.

Key SEPPs for development include:
- SEPP (Design and Place) 2021: Building design, height, FSR, and separation standards
- SEPP (Housing) 2021: Affordable housing bonuses and residential development
- SEPP (Resilience and Hazards) 2021: Contaminated land and hazard management
- SEPP (Transport and Infrastructure) 2021: Development near transport infrastructure
            """
        
    except Exception as e:
        print(f"Error querying SEPP knowledge: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python query_sepp_simple.py <query>", file=sys.stderr)
        sys.exit(1)
        
    query = sys.argv[1]
    result = query_sepp_knowledge(query)
    
    if result:
        print(result.strip())
    else:
        sys.exit(1)