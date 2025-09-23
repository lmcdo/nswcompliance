#!/usr/bin/env python3
"""
ACTUAL SETBACK QUERY CODE FLOW - CONCRETE IMPLEMENTATION
========================================================
Shows exactly what happens when user clicks "Get Setbacks" button
"""

def show_concrete_flow():
 print("ACTUAL SETBACK QUERY CODE EXECUTION FLOW")
 print("=" * 60)
 print("Example: User clicks 'Calculate Setbacks' for '123 Smith St, Marrickville'")
 print()
 
 print("STEP 1: FRONTEND BUTTON CLICK")
 print("- File: frontend/index.html")
 print("- Event: click on 'Calculate Setbacks' button")
 print("- JavaScript: fetch('/calculate-setbacks-council', {method: 'POST'})")
 print()
 
 print("STEP 2: API ENDPOINT") 
 print("- File: api_server.py:641")
 print("- Endpoint: @app.post('/calculate-setbacks-council')")
 print("- Function: calculate_setbacks_council_ready()")
 print()
 
 print("STEP 3: PROPERTY LOOKUP")
 print("- File: api_server.py:649")
 print("- Code: property_context = await get_property_dashboard(request.address)")
 print("- Returns: PropertyData(address='123 Smith St', zone='R2', height_limit='8.5m')")
 print()
 
 print("STEP 4: CALCULATOR CALL")
 print("- File: api_server.py:653")
 print("- Code: setback_result = await calculate_authoritative_setbacks_for_council(property_context)")
 print("- Calls: AuthoritativeSetbackCalculator.calculate_authoritative_setbacks()")
 print()
 
 print("STEP 5: SCOPE VALIDATION")
 print("- File: services/authoritative_setback_calculator.py:155")
 print("- Code: scope_validation = self._validate_mvp_scope(property_data)")
 print("- Check: zone == 'R2' and former_council_area == 'Marrickville'")
 print("- Result: {'in_scope': True}")
 print()
 
 print("STEP 6: HARDCODED FALLBACK LOADING")
 print("- File: services/authoritative_setback_calculator.py:132")
 print("- Loads hardcoded values into self.r2_standard_setbacks:")
 print(" 'marrickville': {")
 print(" 'front': {'typical': 6.0, 'source': 'Marrickville DCP 2011 (FALLBACK)'},")
 print(" 'side': {'min': 0.9, 'source': 'IWLEP 2022 + DCP (FALLBACK)'},")
 print(" 'rear': {'min': 6.0, 'source': 'Marrickville DCP 2011 (FALLBACK)'}")
 print(" }")
 print()
 
 print("STEP 7: SETBACK CALCULATION")
 print("- File: services/authoritative_setback_calculator.py:303")
 print("- Function: _step5_calculate_setbacks()")
 print()
 print(" 7a. Height extraction:")
 print(" - Line 308: building_height = float(property_data.height_limit.replace('m', '')) or 8.5")
 print(" - Result: building_height = 8.5")
 print()
 print(" 7b. Standards loading:")
 print(" - Line 311: standards = self.r2_standard_setbacks['marrickville']")
 print(" - Uses hardcoded fallback values")
 print()
 
 print("STEP 8: DATABASE QUERY ATTEMPT (FAILS)")
 print("- File: services/authoritative_setback_calculator.py:315")
 print("- Code: front_setback = await self._calculate_front_setback_with_lightrag(property_data)")
 print()
 print(" 8a. Universal Engine Call:")
 print(" - File: services/authoritative_setback_calculator.py:364")
 print(" - Code: engine = UniversalRegulatoryEngine()")
 print(" - Code: framework = engine.discover_regulatory_framework(property_data)")
 print()
 print(" 8b. Query Processor Connection:")
 print(" - File: services/universal_regulatory_engine.py:41")
 print(" - Code: from scripts.validated_nsw_query import query_validated_processor")
 print(" - RESULT: ImportError! File 'scripts/validated_nsw_query.py' does not exist")
 print(" - Fallback: self.query_processor = None")
 print()
 print(" 8c. Query Failure:")
 print(" - File: services/universal_regulatory_engine.py:174")
 print(" - Code: if not self.query_processor: return {'error': 'No setback controls available'}")
 print(" - RESULT: Returns error, no database access")
 print()
 
 print("STEP 9: FALLBACK TO HARDCODED VALUES")
 print("- Back to: services/authoritative_setback_calculator.py:315")
 print("- Code: front_setback = None or standards['front']['typical']")
 print("- RESULT: Uses hardcoded 6.0m (not from regulatory database)")
 print()
 
 print("STEP 10: CALCULATIONS (ALL HARDCODED)")
 print("- File: services/authoritative_setback_calculator.py:318-330")
 print()
 
 # Show actual calculations
 building_height = 8.5
 side_base = 0.9
 height_threshold = 8.5
 side_adjustment_factor = 0.5
 rear_base = 6.0
 rear_height_factor = 0.25
 
 print(" Front setback:")
 front_setback = 6.0 # Hardcoded fallback
 print(f" - front_setback = {front_setback}m (HARDCODED FALLBACK)")
 print()
 
 print(" Side setback:")
 print(f" - side_base = {side_base}m")
 print(f" - building_height ({building_height}m) <= height_threshold ({height_threshold}m)")
 print(f" - No height adjustment needed")
 side_setback = side_base
 print(f" - side_setback = {side_setback}m (HARDCODED FALLBACK)")
 print()
 
 print(" Rear setback:")
 rear_height_based = building_height * rear_height_factor
 rear_setback = max(rear_base, rear_height_based)
 print(f" - rear_base = {rear_base}m")
 print(f" - rear_height_based = {building_height} * {rear_height_factor} = {rear_height_based}m")
 print(f" - rear_setback = max({rear_base}, {rear_height_based}) = {rear_setback}m (HARDCODED FALLBACK)")
 print()
 
 print("STEP 11: RESPONSE ASSEMBLY")
 print("- File: services/authoritative_setback_calculator.py:332")
 print("- Returns dictionary with:")
 print(" {")
 print(f" 'front': {{'distance': {front_setback}, 'data_source': 'HARDCODED FALLBACK'}},")
 print(f" 'side': {{'distance': {side_setback}, 'source': 'IWLEP 2022 + DCP (FALLBACK)'}},")
 print(f" 'rear': {{'distance': {rear_setback}, 'source': 'Marrickville DCP 2011 (FALLBACK)'}}")
 print(" }")
 print()
 
 print("STEP 12: API RESPONSE")
 print("- File: api_server.py:657")
 print("- Returns to frontend:")
 print(" {")
 print(" 'success': True,")
 print(f" 'setbacks': {{ front: {front_setback}m, side: {side_setback}m, rear: {rear_setback}m }},")
 print(" 'confidence_grade': 'MEDIUM',")
 print(" 'regulatory_sources': ['Inner West LEP 2022', 'Marrickville DCP 2011']")
 print(" }")
 print()

def show_key_problems():
 print("KEY PROBLEMS IN CURRENT IMPLEMENTATION:")
 print("=" * 60)
 print()
 print("1. NO DATABASE ACCESS")
 print(" - Location: services/universal_regulatory_engine.py:41")
 print(" - Issue: ImportError - scripts.validated_nsw_query does not exist")
 print(" - Impact: 100% fallback to hardcoded values")
 print()
 print("2. NO PAGE CITATIONS")
 print(" - Issue: No page numbers or section references returned")
 print(" - Impact: Non-compliant for council submission")
 print()
 print("3. HARDCODED VALUES")
 print(" - Location: services/authoritative_setback_calculator.py:132")
 print(" - Issue: All setback values are static, not from regulatory database")
 print(" - Impact: May be outdated or incorrect")
 print()
 print("4. NO VISUAL CONTENT") 
 print(" - Issue: No integration with AutoSchemaKG diagrams")
 print(" - Impact: Missing visual regulatory guidance")
 print()
 print("5. NO CLAUSE RELATIONSHIPS")
 print(" - Issue: No LangExtract clause-to-clause connections")
 print(" - Impact: Incomplete regulatory context")

def show_database_reality():
 print("\nDATABASE REALITY CHECK:")
 print("=" * 60)
 
 try:
 import sqlite3
 conn = sqlite3.connect('nsw_planning.db')
 cur = conn.cursor()
 
 tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
 print(f"Available tables: {[t[0] for t in tables]}")
 
 if ('regulatory_refs',) in tables:
 count = cur.execute("SELECT COUNT(*) FROM regulatory_refs").fetchone()[0]
 print(f"regulatory_refs entries: {count:,}")
 
 # Check for setback content
 setback_count = cur.execute("SELECT COUNT(*) FROM regulatory_refs WHERE content LIKE '%setback%'").fetchone()[0]
 print(f"Entries containing 'setback': {setback_count:,}")
 
 # Check page numbers
 page_count = cur.execute("SELECT COUNT(*) FROM regulatory_refs WHERE page_number IS NOT NULL AND page_number > 0").fetchone()[0]
 print(f"Entries with page numbers: {page_count:,}")
 
 if setback_count > 0:
 sample = cur.execute("SELECT ref_type, content, page_number FROM regulatory_refs WHERE content LIKE '%setback%' AND page_number IS NOT NULL LIMIT 2").fetchall()
 print("\nSample setback entries with page numbers:")
 for ref_type, content, page_num in sample:
 print(f"- Page {page_num}: {content[:80]}...")
 
 conn.close()
 
 except Exception as e:
 print(f"DATABASE ACCESS FAILED: {e}")
 print("The code expects database access but database is not accessible")

def show_enhanced_solution():
 print("\nENHANCED SOLUTION WITH PROPER DATABASE:")
 print("=" * 60)
 print()
 print("STEP 8 ENHANCED: SUCCESSFUL DATABASE QUERY")
 print("- Code: result = self.query_processor('R2 front setback requirements')")
 print("- SQL: SELECT content, page_number, section_header FROM regulatory_refs")
 print(" WHERE zone='R2' AND content LIKE '%front%setback%'")
 print()
 print("Database returns:")
 print("- Page 23, Section 4.2: 'Front building setback minimum 6 metres'")
 print("- Page 156, Section 8.3: 'Heritage areas may vary front setback'")
 print()
 print("RESULT: Database-driven calculation with page-perfect citations")
 print("Response includes:")
 print("- Exact regulatory text with page numbers")
 print("- Visual diagrams from AutoSchemaKG") 
 print("- Related clause connections from LangExtract")
 print("- Full compliance documentation for council submission")

def main():
 show_concrete_flow()
 show_key_problems()
 show_database_reality()
 show_enhanced_solution()

if __name__ == "__main__":
 main()