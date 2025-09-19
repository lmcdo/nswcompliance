from db_config import get_connection
import re

conn = get_connection()
cursor = conn.cursor()

print('=== PRP-Q2 QUANTITATIVE EXTRACTION ANALYSIS ===')

print('\n1. SEPP QUANTITATIVE EXTRACTION RELIABILITY:')
print('Found SEPP provisions with numeric content - examples:')
print('- "minimum lot size of 500m²" -> lot_size: 500 sqm')
print('- "at least 40% of lighting fixtures" -> percentage: 40%')
print('- "total new floor area of up to 15m²" -> area: 15 sqm')
print('- "a rainwater tank within 10m of edge" -> setback: 10m')

print('\n2. NSW API QUANTITIES INTEGRATION:')
print('Current NSW API provides:')
print('- Raw special provisions with Type/Category/Legislative Clause')
print('- BASIX climate zones ("Zone 17", "Zone 18", etc.)')
print('- SEPP identifications with clause references')
print('- Numeric values embedded in provision text')

print('\n3. CLIMATE ZONE -> ENERGY/WATER TARGET LINKAGE:')
cursor.execute('''
    SELECT climate_zone, development_type,
           energy_reduction_target, water_reduction_target
    FROM basix_provisions
    ORDER BY climate_zone, development_type
''')

print('Verified BASIX mappings in database:')
for zone, dev_type, energy, water in cursor.fetchall():
    print(f'  {zone} + {dev_type}: {energy}% energy reduction, {water}% water reduction')

print('\n4. TIER AUTHORITY ASSIGNMENTS:')
cursor.execute('''
    SELECT provision_type, default_tier_level, authority_level, requires_specialist
    FROM special_provisions_registry
    ORDER BY default_tier_level, authority_level DESC
''')

print('Provision hierarchy (Tier -> Authority Level -> Specialist Required):')
for prov_type, tier, authority, specialist in cursor.fetchall():
    specialist_flag = ' [SPECIALIST]' if specialist else ''
    print(f'  Tier {tier}: {prov_type} ({authority}% authority){specialist_flag}')

print('\n=== PRP-Q2 PROCESSING ENGINE STRATEGY ===')

print('\nA. RELIABLE QUANTITATIVE EXTRACTION:')
print('1. Regex Pattern Matching:')
patterns = {
    'lot_size': r'(\d+(?:\.\d+)?)\s*(?:square\s*metres?|sqm|m²|m2)',
    'height': r'(\d+(?:\.\d+)?)\s*(?:metres?|m)\s*(?:high|height|above)',
    'setback': r'(\d+(?:\.\d+)?)\s*(?:metres?|m)\s*(?:setback|from)',
    'percentage': r'(\d+(?:\.\d+)?)\s*(?:%|percent)',
    'floor_space_ratio': r'(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)|FSR.*?(\d+\.\d+)'
}

for name, pattern in patterns.items():
    print(f'   {name}: {pattern}')

print('\n2. Context-Aware Extraction:')
print('   - Match numbers only when followed by relevant units')
print('   - Use SEPP clause context (3.31 = housing diversity, 3.32 = manor houses)')
print('   - Cross-reference with known SEPP provision mappings')

print('\nB. NSW API INTEGRATION FLOW:')
print('1. Raw Special Provisions -> Type/Category identification')
print('2. SEPP clause matching -> Known provision lookup')
print('3. Numeric extraction -> Value + unit + context')
print('4. Tier assignment -> Authority level determination')

print('\nC. CLIMATE ZONE LINKAGE:')
print('1. NSW API extracts: "Climate Zones" Type, "Zone 17" Class')
print('2. PRP-Q1 database lookup: Zone 17 + dwelling_house = 40% energy, 40% water')
print('3. Tier 1 provision: 100% authority, immediate compliance requirement')

print('\nD. AUTHORITY TIER SYSTEM:')
print('Tier 1 (90-100% authority): BASIX, Flood Planning, Bushfire - immediate compliance')
print('Tier 2 (80-90% authority): Heritage, Acid Sulfate - specialist assessment')
print('Tier 3 (70-80% authority): General LEP provisions - council discretion')
print('Tier 4 (60-70% authority): Advisory guidelines - best practice')
print('Tier 5 (<60% authority): Historical/reference - context only')

print('\n=== IMPLEMENTATION RELIABILITY MEASURES ===')
print('1. Fallback Strategies:')
print('   - If regex fails, flag for manual review')
print('   - Default to qualitative assessment with specialist flag')
print('   - Conservative approach: higher tier when uncertain')

print('\n2. Validation Mechanisms:')
print('   - Cross-check extracted values against known SEPP ranges')
print('   - Flag outliers for review (e.g., 50000m² lot size)')
print('   - Confidence scoring based on pattern match strength')

print('\n3. Data Quality Assurance:')
print('   - Log all extractions for audit trail')
print('   - Track extraction success rates by provision type')
print('   - Regular updates to SEPP clause mappings')

conn.close()