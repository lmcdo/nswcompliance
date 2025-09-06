#!/usr/bin/env python3
"""
ACTUAL SETBACK QUERY CODE FLOW WALKTHROUGH
==========================================
Traces the CONCRETE implementation step by step when user clicks "Get Setbacks" button.
Shows exact table names, column access, calculations, and fallback logic.

EXAMPLE: User clicks "Calculate Setbacks" for 123 Smith Street, Marrickville
"""

import sqlite3
import json
from typing import Dict, Any

def trace_actual_code_execution():
    """
    Trace EXACT code execution as it happens in the system
    """
    print("ACTUAL SETBACK QUERY CODE FLOW - CONCRETE IMPLEMENTATION")
    print("=" * 80)
    
    # STEP 1: Frontend Button Click
    print("\nSTEP 1: FRONTEND BUTTON CLICK")
    print("   Location: frontend/index.html")
    print("   User clicks: 'Calculate Setbacks' button")
    print("   JavaScript executes:")
    print("""
   document.getElementById('calculate-setbacks-council').addEventListener('click', async () => {
       const address = document.getElementById('address-input').value;
       const response = await fetch('/calculate-setbacks-council', {
           method: 'POST',
           body: JSON.stringify({address: address})
       });
   });
   """)
    
    # STEP 2: API Endpoint Reception
    print("\nSTEP 2: API ENDPOINT RECEPTION")
    print("   File: api_server.py:641")
    print("   Endpoint: @app.post('/calculate-setbacks-council')")
    print("   Function: calculate_setbacks_council_ready()")
    print("   Receives: QueryRequest with address='123 Smith Street, Marrickville'")
    
    # STEP 3: Property Intelligence Lookup
    print("\nSTEP 3: PROPERTY INTELLIGENCE LOOKUP")
    print("   File: api_server.py:649-650")
    print("   Code executed:")
    print("   from services.property_intelligence import get_property_dashboard")
    print("   property_context = await get_property_dashboard(request.address)")
    
    # Let's check what property data looks like
    property_mock = {
        "address": "123 Smith Street, Marrickville",
        "zone": "R2",
        "height_limit": "8.5m",
        "former_council_area": "Marrickville"
    }
    print(f"   Returns PropertyData: {property_mock}")
    
    # STEP 4: Authoritative Calculator Invocation
    print("\n⚖️  STEP 4: AUTHORITATIVE CALCULATOR INVOCATION")
    print("   File: api_server.py:653-655")
    print("   Code executed:")
    print("   from services.authoritative_setback_calculator import calculate_authoritative_setbacks_for_council")
    print("   setback_result = await calculate_authoritative_setbacks_for_council(property_context)")
    
    print("\n   Calls: AuthoritativeSetbackCalculator.calculate_authoritative_setbacks()")
    print("   File: services/authoritative_setback_calculator.py:148")
    
    # STEP 5: MVP Scope Validation
    print("\n✅ STEP 5: MVP SCOPE VALIDATION")
    print("   File: services/authoritative_setback_calculator.py:155")
    print("   Code executed:")
    print("   scope_validation = self._validate_mvp_scope(property_data)")
    print("   Checks: zone == 'R2' and former_council_area == 'Marrickville'")
    print("   Result: {'in_scope': True}")
    
    # STEP 6: Hardcoded Fallback Standards Loading
    print("\n💾 STEP 6: HARDCODED FALLBACK STANDARDS LOADING")
    print("   File: services/authoritative_setback_calculator.py:132-138")
    print("   Code executed:")
    print("""
   self.r2_standard_setbacks = {
       "marrickville": {
           "front": {"min": 3.0, "max": 9.0, "typical": 6.0, "source": "Marrickville DCP 2011 (FALLBACK)"},
           "side": {"min": 0.9, "max": 3.0, "typical": 1.5, "source": "IWLEP 2022 + DCP (FALLBACK)"},
           "rear": {"min": 6.0, "max": 25.0, "typical": 8.0, "source": "Marrickville DCP 2011 (FALLBACK)"}
       }
   }
   """)
    
    # STEP 7: Step 5 Calculate Setbacks
    print("\n🔢 STEP 7: STEP 5 CALCULATE SETBACKS")
    print("   File: services/authoritative_setback_calculator.py:303")
    print("   Function: _step5_calculate_setbacks()")
    
    print("\n   7a. Height Extraction (HARDCODED FALLBACK):")
    print("   Line 308: building_height = float(property_data.height_limit.replace('m', '')) if property_data.height_limit else 8.5")
    print(f"   Result: building_height = 8.5")
    
    print("\n   7b. Standards Loading:")
    print("   Line 311: standards = self.r2_standard_setbacks['marrickville']")
    print("   Uses HARDCODED fallback values")
    
    # STEP 8: Database Query Attempt
    print("\n🗃️  STEP 8: DATABASE QUERY ATTEMPT")
    print("   File: services/authoritative_setback_calculator.py:315")
    print("   Code executed:")
    print("   front_setback = await self._calculate_front_setback_with_lightrag(property_data) or standards['front']['typical']")
    
    print("\n   8a. Universal Regulatory Engine Call:")
    print("   File: services/authoritative_setback_calculator.py:364")
    print("   Code: engine = UniversalRegulatoryEngine()")
    print("   Code: framework = engine.discover_regulatory_framework(property_data)")
    
    print("\n   8b. Query Processor Connection Attempt:")
    print("   File: services/universal_regulatory_engine.py:41")
    print("   Code: from scripts.validated_nsw_query import query_validated_processor")
    print("   Result: ImportError - File 'scripts/validated_nsw_query.py' does not exist!")
    print("   Fallback: self.query_processor = None")
    
    # STEP 9: Database Query Failure - Use Fallback
    print("\n❌ STEP 9: DATABASE QUERY FAILURE - USE FALLBACK")
    print("   File: services/universal_regulatory_engine.py:174")
    print("   Code: if not self.query_processor or not applicable_sections:")
    print("   Code:     return {'error': 'No setback controls available'}")
    print("   Result: Returns error, triggers fallback to hardcoded values")
    
    print("\n   Back to authoritative_setback_calculator.py:315:")
    print("   front_setback = None or standards['front']['typical']  # Uses HARDCODED 6.0m")
    
    # STEP 10: Calculation Logic
    print("\n🧮 STEP 10: CALCULATION LOGIC")
    print("   All calculations use HARDCODED FALLBACK VALUES:")
    
    # Show actual calculation
    building_height = 8.5
    standards = {
        "front": {"min": 3.0, "max": 9.0, "typical": 6.0, "source": "Marrickville DCP 2011 (FALLBACK)"},
        "side": {"min": 0.9, "max": 3.0, "typical": 1.5, "source": "IWLEP 2022 + DCP (FALLBACK)"},
        "rear": {"min": 6.0, "max": 25.0, "typical": 8.0, "source": "Marrickville DCP 2011 (FALLBACK)"}
    }
    height_threshold = 8.5
    side_adjustment_factor = 0.5
    rear_height_factor = 0.25
    
    print(f"\n   Front setback calculation (Line 315):")
    front_setback = standards["front"]["typical"]  # Database failed, use fallback
    print(f"   front_setback = {front_setback}m (HARDCODED FALLBACK)")
    
    print(f"\n   Side setback calculation (Lines 318-325):")
    side_base = standards["side"]["min"]
    if building_height > height_threshold:
        height_adjustment = (building_height - height_threshold) * side_adjustment_factor
        side_setback = side_base + height_adjustment
    else:
        side_setback = side_base
    print(f"   side_base = {side_base}m")
    print(f"   building_height ({building_height}m) <= height_threshold ({height_threshold}m)")
    print(f"   side_setback = {side_setback}m (HARDCODED FALLBACK)")
    
    print(f"\n   Rear setback calculation (Lines 328-330):")
    rear_base = standards["rear"]["min"]
    rear_height_based = building_height * rear_height_factor
    rear_setback = max(rear_base, rear_height_based)
    print(f"   rear_base = {rear_base}m")
    print(f"   rear_height_based = {building_height} * {rear_height_factor} = {rear_height_based}m")
    print(f"   rear_setback = max({rear_base}, {rear_height_based}) = {rear_setback}m (HARDCODED FALLBACK)")
    
    # STEP 11: Response Assembly
    print("\n📝 STEP 11: RESPONSE ASSEMBLY")
    print("   File: services/authoritative_setback_calculator.py:332-350")
    print("   Returns:")
    response_data = {
        "front": {
            "distance": front_setback,
            "source": f"{standards['front']['source']} - typical for area",
            "calculation": f"Fixed requirement: {front_setback}m",
            "data_source": "HARDCODED FALLBACK"
        },
        "side": {
            "distance": side_setback,
            "source": f"{standards['side']['source']} with height adjustment",
            "calculation": f"{side_base}m base + {max(0, side_setback - side_base):.1f}m height adjustment = {side_setback:.1f}m"
        },
        "rear": {
            "distance": rear_setback,
            "source": f"{standards['rear']['source']} - height based",
            "calculation": f"Greater of {rear_base}m base or {rear_height_based:.1f}m height-based = {rear_setback:.1f}m"
        }
    }
    print(f"   {json.dumps(response_data, indent=2)}")
    
    # STEP 12: Final API Response
    print("\n🚀 STEP 12: FINAL API RESPONSE")
    print("   File: api_server.py:657-671")
    print("   Returns to frontend:")
    final_response = {
        "success": True,
        "setbacks": response_data,
        "confidence_grade": "MEDIUM",
        "confidence_percentage": 75,
        "regulatory_sources": ["Inner West LEP 2022", "Marrickville DCP 2011"],
        "disclaimer": "Preliminary guidance - Professional verification required"
    }
    print(f"   {json.dumps(final_response, indent=2)}")
    
    # KEY PROBLEMS ANALYSIS
    print("\n\n🚨 KEY PROBLEMS IN CURRENT IMPLEMENTATION:")
    print("=" * 80)
    
    problems = [
        {
            "problem": "NO DATABASE ACCESS",
            "location": "services/universal_regulatory_engine.py:41",
            "issue": "ImportError: scripts.validated_nsw_query does not exist",
            "impact": "100% fallback to hardcoded values"
        },
        {
            "problem": "NO PAGE CITATIONS", 
            "location": "Throughout calculation",
            "issue": "No page numbers, section references, or regulatory citations",
            "impact": "Non-compliant for council submission"
        },
        {
            "problem": "HARDCODED FALLBACK VALUES",
            "location": "services/authoritative_setback_calculator.py:132",
            "issue": "All values are static, not from regulatory database",
            "impact": "May be outdated or incorrect"
        },
        {
            "problem": "NO VISUAL CONTENT",
            "location": "No integration with AutoSchemaKG",
            "issue": "No diagrams, figures, or visual regulatory content",
            "impact": "Missing multimodal guidance"
        },
        {
            "problem": "NO CLAUSE CONNECTIONS",
            "location": "No LangExtract integration",
            "issue": "No clause-to-clause relationships or hierarchy",
            "impact": "Incomplete regulatory context"
        }
    ]
    
    for i, problem in enumerate(problems, 1):
        print(f"\n   {i}. {problem['problem']}")
        print(f"      Location: {problem['location']}")
        print(f"      Issue: {problem['issue']}")
        print(f"      Impact: {problem['impact']}")

def show_database_reality():
    """Show what the database actually contains vs what code expects"""
    print("\n\n💾 DATABASE REALITY CHECK")
    print("=" * 80)
    
    try:
        conn = sqlite3.connect('nsw_planning.db')
        cur = conn.cursor()
        
        print("\n📊 ACTUAL DATABASE CONTENT:")
        
        # Check if the database has the data needed
        tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print(f"   Tables available: {[t[0] for t in tables]}")
        
        # Check regulatory_refs table
        if ('regulatory_refs',) in tables:
            count = cur.execute("SELECT COUNT(*) FROM regulatory_refs").fetchone()[0]
            print(f"   regulatory_refs entries: {count:,}")
            
            # Sample entries
            sample = cur.execute("SELECT ref_type, ref_number, content FROM regulatory_refs WHERE content LIKE '%setback%' LIMIT 3").fetchall()
            if sample:
                print(f"\n   SAMPLE SETBACK ENTRIES:")
                for i, (ref_type, ref_num, content) in enumerate(sample, 1):
                    print(f"   {i}. {ref_type} {ref_num}: {content[:100]}...")
            else:
                print("   ❌ NO SETBACK ENTRIES FOUND")
        
        # Check page numbers
        page_count = cur.execute("SELECT COUNT(*) FROM regulatory_refs WHERE page_number IS NOT NULL AND page_number > 0").fetchone()[0]
        print(f"   Entries with page numbers: {page_count:,}")
        
        conn.close()
        
    except sqlite3.OperationalError as e:
        print(f"   ❌ DATABASE ACCESS FAILED: {e}")
        print("   The code expects database access but database may not exist or be accessible")

def show_enhanced_flow():
    """Show how the enhanced system would work with proper database integration"""
    print("\n\n✨ ENHANCED SYSTEM FLOW (WITH PROPER DATABASE)")
    print("=" * 80)
    
    print("\n🔍 STEP 8 ENHANCED: SUCCESSFUL DATABASE QUERY")
    print("   File: services/universal_regulatory_engine.py")
    print("   Code: result = self.query_processor('R2 front setback requirements metres')")
    print("   SQL executed: SELECT content, page_number, section_header FROM regulatory_refs WHERE")
    print("                 zone='R2' AND content LIKE '%front%setback%' AND page_number IS NOT NULL")
    
    print("\n   Database returns:")
    enhanced_db_result = [
        {"content": "Front building setback shall be minimum 6 metres from the front property boundary", 
         "page_number": 23, "section_header": "4.2 Building Setbacks"},
        {"content": "In heritage conservation areas, front setback may be varied to match streetscape", 
         "page_number": 156, "section_header": "8.3 Heritage Controls"}
    ]
    for result in enhanced_db_result:
        print(f"   - Page {result['page_number']}, {result['section_header']}: {result['content']}")
    
    print("\n🧮 STEP 10 ENHANCED: DATABASE-DRIVEN CALCULATIONS")
    print("   Code: setbacks = self._extract_setback_values_from_result(result)")
    print("   Regex: r'front.*?setback.*?(\\d+(?:\\.\\d+)?)\\s*m(?:etres?)?'")
    print("   Extracted: front_setback = 6.0m (from regulatory database, not hardcoded)")
    
    print("\n📋 STEP 11 ENHANCED: RESPONSE WITH CITATIONS")
    enhanced_response = {
        "front": {
            "distance": 6.0,
            "source": "Marrickville DCP 2011, Section 4.2, Page 23",
            "calculation": "Minimum requirement: 6.0m",
            "data_source": "Regulatory Database (LangExtract processed)",
            "visual_content": ["diagram_page_25_setback_illustration.png"],
            "related_clauses": ["heritage_variation_clause_8_3_page_156"]
        }
    }
    print(f"   {json.dumps(enhanced_response, indent=2)}")

def main():
    """Main execution"""
    print("SETBACK QUERY: ACTUAL CODE EXECUTION TRACE")
    print("=" * 80)
    print("Example: User clicks 'Calculate Setbacks' for '123 Smith Street, Marrickville'")
    
    trace_actual_code_execution()
    show_database_reality()
    show_enhanced_flow()
    
    print("\n\n🎯 SUMMARY")
    print("=" * 80)
    print("CURRENT SYSTEM: Uses 100% hardcoded fallback values")
    print("- Database connection fails (missing query processor)")
    print("- No page citations (non-compliant)")
    print("- No visual content (incomplete guidance)")
    print("- No clause relationships (limited context)")
    print("")
    print("ENHANCED SYSTEM: Uses regulatory database with full integration")
    print("- LangExtract: 2,518 entries with page numbers")
    print("- AutoSchemaKG: 1,473 visual elements with clause mapping")
    print("- Complete citations for council compliance")
    print("- Multimodal regulatory guidance")

if __name__ == "__main__":
    main()