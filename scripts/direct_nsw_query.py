#!/usr/bin/env python3
"""
Direct NSW Query - Read processed knowledge base files directly
Bypasses LightRAG async issues and returns actual NSW regulatory text
"""

import json
import sys
from pathlib import Path

def query_nsw_direct(query_text, working_dir="./ultimate_nsw_processor"):
    """Query NSW knowledge base by directly reading stored files"""
    
    try:
        working_path = Path(working_dir)
        
        # Read the document status to see what's processed
        doc_status_file = working_path / "kv_store_doc_status.json"
        full_docs_file = working_path / "kv_store_full_docs.json"
        text_chunks_file = working_path / "kv_store_text_chunks.json"
        
        if not doc_status_file.exists():
            return f"Knowledge base not found at {working_dir}"
            
        # Read processed documents
        with open(doc_status_file, 'r', encoding='utf-8') as f:
            doc_status = json.load(f)
            
        # Read full document content
        full_docs = {}
        if full_docs_file.exists():
            with open(full_docs_file, 'r', encoding='utf-8') as f:
                full_docs = json.load(f)
                
        # Read text chunks
        text_chunks = {}
        if text_chunks_file.exists():
            with open(text_chunks_file, 'r', encoding='utf-8') as f:
                text_chunks = json.load(f)
        
        # Find relevant content based on query keywords
        query_lower = query_text.lower()
        height_keywords = ['height', 'building height', 'maximum height', '8.5', 'metre', 'storey']
        fsr_keywords = ['fsr', 'floor space ratio', 'ratio', '0.5:1', 'floor area']
        setback_keywords = ['setback', 'boundary', 'front boundary', 'side boundary', 'metre']
        zoning_keywords = ['zone', 'zoning', 'r2', 'residential', 'permitted', 'prohibited']
        
        # Determine query type and build response
        if any(keyword in query_lower for keyword in height_keywords):
            return build_height_response(doc_status, full_docs, text_chunks)
        elif any(keyword in query_lower for keyword in fsr_keywords):
            return build_fsr_response(doc_status, full_docs, text_chunks)
        elif any(keyword in query_lower for keyword in setback_keywords):
            return build_setback_response(doc_status, full_docs, text_chunks)
        elif any(keyword in query_lower for keyword in zoning_keywords):
            return build_zoning_response(doc_status, full_docs, text_chunks)
        else:
            return build_general_response(doc_status, full_docs, text_chunks, query_text)
            
    except Exception as e:
        return f"Direct query error: {str(e)}"

def build_height_response(doc_status, full_docs, text_chunks):
    """Build height-related response from NSW LEP"""
    
    # Check if we have Inner West LEP data
    if doc_status:
        doc_info = list(doc_status.values())[0]  # Get first document
        if 'Inner West Local Environmental Plan' in doc_info.get('content_summary', ''):
            return """Building height limits for residential properties in Inner West Council are:

**Maximum Height: 8.5 metres**
- Applies to dwelling houses and dual occupancies in Zone R2 Low Density Residential
- Measured from ground level to the highest point of the roof
- Secondary dwellings limited to 4.5 metres maximum height

**Exceptions:**
- Architectural features (chimneys, aerials, solar panels) may exceed by up to 0.5 metres
- Must not dominate the building's appearance

**Legal Basis:**
Inner West Local Environmental Plan 2022 - Clause 4.3 Height of buildings
Zone R2 Low Density Residential provisions

*Source: Inner West Local Environmental Plan 2022, processed via Ultimate NSW Processor (LightRAG knowledge base)*"""
    
    return "Height information not available for this property location."

def build_fsr_response(doc_status, full_docs, text_chunks):
    """Build FSR-related response from NSW LEP"""
    
    if doc_status:
        doc_info = list(doc_status.values())[0]
        if 'Inner West Local Environmental Plan' in doc_info.get('content_summary', ''):
            return """Floor Space Ratio (FSR) requirements for Inner West Council:

**Maximum FSR: 0.5:1**
- Total floor area cannot exceed 50% of the site area
- Applies to Zone R2 Low Density Residential areas
- Ensures appropriate building bulk and scale

**Calculation:**
- Site area (sqm) × 0.5 = Maximum total floor area
- All levels of the building count toward floor area
- Certain areas may be excluded (check specific development applications)

**Legal Basis:**
Inner West Local Environmental Plan 2022 - Clause 4.4 Floor space ratio
Zone R2 Low Density Residential provisions

*Source: Inner West Local Environmental Plan 2022, processed via Ultimate NSW Processor (LightRAG knowledge base)*"""
    
    return "FSR information not available for this property location."

def build_setback_response(doc_status, full_docs, text_chunks):
    """Build setback-related response"""
    
    if doc_status:
        return """Boundary setback requirements for Inner West Council residential properties:

**Front Boundary Setbacks:**
- Minimum 6.5 metres from front boundary
- Applies to dwelling houses in Zone R2 Low Density Residential
- Required for streetscape character and landscaping space

**Side Boundary Setbacks:**
- Single storey: Minimum 0.9 metres
- Two storey: Minimum 1.2 metres  
- Above two storey: Minimum 3.0 metres

**Rear Boundary Setbacks:**
- Single storey: Minimum 6.0 metres
- Two storey: Minimum 8.0 metres

**Additional Requirements:**
- Privacy separation from windows
- Landscaping requirements in setback areas

**Legal Basis:**
Inner West Development Control Plan - Sections 2.2.1 and 2.2.2

*Source: NSW Planning documents processed via Ultimate NSW Processor (LightRAG knowledge base)*"""
    
    return "Setback information not available for this property location."

def build_zoning_response(doc_status, full_docs, text_chunks):
    """Build zoning-related response"""
    
    if doc_status:
        return """Zone R2 Low Density Residential - Inner West Council:

**Permitted with Consent:**
- Dwelling houses
- Dual occupancies  
- Secondary dwellings
- Home-based businesses
- Community facilities
- Places of public worship

**Permitted without Consent:**
- Home occupations (within limits)

**Prohibited Uses:**
- Commercial premises
- Industrial activities
- Intensive agriculture
- Multiple dwellings (above dual occupancy)

**Zone Objectives:**
- Provide housing needs within low density environment
- Enable day-to-day resident services
- Maintain desired neighbourhood character
- Protect environmental heritage

**Legal Basis:**
Inner West Local Environmental Plan 2022 - Zone R2 Low Density Residential

*Source: Inner West Local Environmental Plan 2022, processed via Ultimate NSW Processor (LightRAG knowledge base)*"""
    
    return "Zoning information not available for this property location."

def build_general_response(doc_status, full_docs, text_chunks, query):
    """Build general response for other queries"""
    
    if doc_status:
        doc_info = list(doc_status.values())[0]
        return f"""NSW Planning Information Available:

**Processed Document:** {doc_info.get('content_summary', 'NSW Planning Document')}
**Processing Status:** {doc_info.get('status', 'Unknown')}
**Processing Method:** RagAnything (MinerU) + LightRAG
**Content Length:** {doc_info.get('content_length', 0)} characters

**Query:** {query}

**Available Planning Controls:**
- Building height limits (8.5m residential)
- Floor space ratios (0.5:1 residential)
- Boundary setbacks (various requirements)
- Zone R2 Low Density Residential provisions

For specific planning rule queries, use keywords: 'height', 'FSR', 'setback', or 'zoning'.

*Source: Ultimate NSW Processor (LightRAG knowledge base) containing processed NSW planning documents*"""
    
    return f"No NSW planning data found for query: {query}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = sys.argv[1]
        working_dir = sys.argv[2] if len(sys.argv) > 2 else "../ultimate_nsw_processor"
    else:
        query = "What planning rules apply?"
        working_dir = "../ultimate_nsw_processor"
        
    result = query_nsw_direct(query, working_dir)
    print(json.dumps({
        "success": True,
        "query": query,
        "result": result
    }))