#!/usr/bin/env python3
"""
Comprehensive Regulatory Entity Extraction Pipeline
==================================================
Extract ALL regulatory entities, not just formal clauses.
Captures zones, standards, overlays, SEPPs, assessment criteria, etc.
"""

import google.generativeai as genai
import json
import os
import re
import sqlite3
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path
from monitored_4stack_pipeline import MonitoredPipeline

class ComprehensiveExtractionPipeline(MonitoredPipeline):
    """Enhanced pipeline with comprehensive entity extraction"""
    
    def extract_from_document(self, doc_id, pdf_name, full_text):
        """Extract with COMPREHENSIVE entity coverage"""
        
        # Chunk intelligently
        max_chunk_size = 8000
        chunks = self.intelligent_chunk(full_text, max_chunk_size)
        
        print(f"  Chunks: {len(chunks)} ({len(full_text):,} chars)")
        
        all_results = {
            'entities': [],
            'relationships': [],
            'provisions': []
        }
        
        for chunk_idx, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            
            print(f"    [{chunk_idx + 1}/{len(chunks)}] ", end="")
            
            # Rate limiting
            self.enforce_rate_limit()
            
            # COMPREHENSIVE extraction prompt
            prompt = f"""
COMPREHENSIVE REGULATORY ENTITY EXTRACTION

Document: {pdf_name}
Extract ALL regulatory and legislative elements from this NSW planning text.

ENTITY CATEGORIES TO EXTRACT:

1. ZONING & LAND USE:
   - Zones: R1, R2, R3, R4, B1, B2, B4, B6, IN1, IN2, RE1, E1, etc.
   - Land uses: "Multi dwelling housing", "Seniors housing", "Child care centres"
   - Permissible/prohibited uses

2. DEVELOPMENT STANDARDS:
   - "Height of buildings", "Floor space ratio", "Minimum lot size"
   - "Building envelope", "Site coverage", "Landscaped area"

3. DESIGN CONTROLS:
   - "Front setback", "Side setback", "Rear setback"  
   - "Building height", "Deep soil", "Private open space"

4. ASSESSMENT CATEGORIES:
   - "Complying development", "Merit assessment", "Impact assessment"
   - "State significant development"

5. OVERLAY CONTROLS:
   - "Heritage conservation area", "Heritage item"
   - "Flood planning area", "Bushfire prone land", "Contaminated land"

6. SEPP REFERENCES:
   - "SEPP 65", "SEPP Housing 2021", "SEPP Infrastructure"
   - "Codes SEPP", "SEPP Affordable Rental Housing"

7. ASSESSMENT CRITERIA:
   - "BASIX", "Disability access", "Car parking rates"
   - "Bicycle parking", "Waste management"

8. PROCEDURAL REFERENCES:
   - "Section 4.15" (EP&A Act), "Section 4.16", "Part 4"

9. TECHNICAL STANDARDS:
   - "Australian Standards", "AS 2890.1", "Building Code of Australia"
   - "National Construction Code", "Access to Premises Standards"

10. COUNCIL-SPECIFIC:
    - DCP sections, "Planning agreements", "Contributions plans"
    - "Additional provisions", "Local provisions"

TEXT TO ANALYZE:
{chunk[:6000]}

RETURN JSON:
{{
  "entities": [
    {{
      "type": "zone|land_use|development_standard|design_control|assessment|overlay|sepp|criteria|procedure|technical|council|clause|section",
      "reference": "exact reference or name",
      "text": "first 80 chars of text",
      "category": "specific category like 'zoning' or 'heritage'"
    }}
  ],
  "relationships": [
    {{
      "source": "source entity",
      "target": "target entity", 
      "type": "refers_to|in_accordance_with|subject_to|applies_to|overrides",
      "evidence": "exact text showing relationship"
    }}
  ],
  "provisions": [
    {{
      "entity": "what entity this provision relates to",
      "type": "setback|height|fsr|parking|design|heritage|zone|assessment",
      "text": "regulatory text",
      "measurement": "specific measurements/values",
      "applies_to": "what it applies to"
    }}
  ]
}}
"""
            
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=2000,
                        temperature=0.1
                    )
                )
                
                if response and response.text:
                    # Parse response
                    json_text = self.clean_json(response.text)
                    data = json.loads(json_text)
                    
                    # Verify and collect
                    entities = data.get('entities', [])
                    relationships = data.get('relationships', [])
                    provisions = data.get('provisions', [])
                    
                    # Enhanced verification - check multiple fields
                    verified_entities = 0
                    for entity in entities:
                        ref = entity.get('reference', '')
                        text = entity.get('text', '')
                        
                        # Check if reference OR significant text exists in chunk
                        if (ref and (ref in chunk or ref.replace(' ', '') in chunk.replace(' ', ''))) or \
                           (text and len(text) > 10 and text[:30] in chunk):
                            verified_entities += 1
                            entity['verified'] = True
                        else:
                            entity['verified'] = False
                    
                    all_results['entities'].extend(entities)
                    all_results['relationships'].extend(relationships) 
                    all_results['provisions'].extend(provisions)
                    
                    print(f"E:{len(entities)} R:{len(relationships)} P:{len(provisions)} V:{verified_entities}")
                    
                    if entities or relationships or provisions:
                        self.stats['successful_extractions'] += 1
                    
                else:
                    print("[EMPTY]")
                    self.stats['failed_extractions'] += 1
                    
            except json.JSONDecodeError:
                print("[JSON_ERROR]")
                self.stats['failed_extractions'] += 1
                self.log_error(f"{pdf_name} chunk {chunk_idx}: JSON parse error")
                
            except Exception as e:
                print(f"[ERROR: {str(e)[:20]}]")
                self.stats['failed_extractions'] += 1
                self.log_error(f"{pdf_name} chunk {chunk_idx}: {str(e)}")
                time.sleep(10)  # Wait on errors
        
        return all_results

    def update_database(self, doc_id, extraction_results):
        """Enhanced database population with comprehensive entities"""
        conn = sqlite3.connect('nsw_planning.db')
        cursor = conn.cursor()
        
        entries_added = 0
        
        try:
            # Add ALL entity types
            for entity in extraction_results.get('entities', []):
                if entity.get('reference'):
                    # Use the specific category and type
                    ref_type = entity.get('category', entity.get('type', 'entity'))
                    cursor.execute("""
                        INSERT INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
                        VALUES (?, ?, ?, ?)
                    """, (doc_id, ref_type, entity.get('reference'), 
                          entity.get('text', '')[:500]))
                    entries_added += 1
            
            # Add relationships as references
            for relationship in extraction_results.get('relationships', []):
                if relationship.get('source') and relationship.get('target'):
                    cursor.execute("""
                        INSERT INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
                        VALUES (?, ?, ?, ?)
                    """, (doc_id, f"relationship_{relationship.get('type')}", 
                          f"{relationship.get('source')} -> {relationship.get('target')}", 
                          relationship.get('evidence', '')[:500]))
                    entries_added += 1
            
            # Add provisions
            for provision in extraction_results.get('provisions', []):
                if provision.get('entity'):
                    cursor.execute("""
                        INSERT INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
                        VALUES (?, ?, ?, ?)
                    """, (doc_id, f"provision_{provision.get('type')}", 
                          provision.get('entity'), provision.get('text', '')[:500]))
                    entries_added += 1
            
            conn.commit()
            
        except Exception as e:
            self.log_error(f"Database error for {doc_id}: {str(e)}")
            conn.rollback()
            
        finally:
            conn.close()
        
        return entries_added

def main():
    """Run comprehensive extraction pipeline"""
    
    print("COMPREHENSIVE REGULATORY EXTRACTION PIPELINE")
    print("=" * 70)
    print("Extracting ALL regulatory entities including:")
    print("- Zones, land uses, development standards")
    print("- Design controls, assessment criteria")  
    print("- Overlay controls, SEPP references")
    print("- Technical standards, procedural references")
    print("- Council-specific provisions")
    print()
    print("Expected extraction increase: 5-10x more entities")
    print("Duration: 4-5 hours")
    print()
    
    try:
        pipeline = ComprehensiveExtractionPipeline()
        
        print("STARTING COMPREHENSIVE PIPELINE...")
        pipeline.process_all_documents()
        
        # Generate enhanced report
        report = pipeline.generate_final_report()
        
        # Check final database state
        conn = sqlite3.connect('nsw_planning.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
        total_refs = cursor.fetchone()[0]
        
        # Get breakdown by type
        cursor.execute("""
            SELECT ref_type, COUNT(*) 
            FROM regulatory_refs 
            GROUP BY ref_type 
            ORDER BY COUNT(*) DESC
        """)
        ref_breakdown = cursor.fetchall()
        conn.close()
        
        print(f"\nCOMPREHENSIVE EXTRACTION COMPLETE")
        print(f"Total regulatory references: {total_refs:,}")
        print(f"\nBreakdown by type:")
        for ref_type, count in ref_breakdown[:15]:
            print(f"  {ref_type}: {count:,}")
        
        return True
        
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Pipeline stopped by user")
        return False
        
    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n[SUCCESS] Comprehensive extraction completed")
    else:
        print("\n[FAILED] Comprehensive extraction failed")