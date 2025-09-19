from db_config import get_connection
import re

conn = get_connection()
cursor = conn.cursor()

print('=== SEPP PROVISIONS ANALYSIS ===')
cursor.execute('SELECT COUNT(*) FROM sepp_provisions')
total = cursor.fetchone()[0]
print(f'Total SEPP provisions: {total:,}')

print('\nSample SEPP provisions with numeric content:')
cursor.execute('''
    SELECT provision_text, ref_number, section_header
    FROM sepp_provisions
    WHERE provision_text ~ '[0-9]+\\.?[0-9]*\\s*(m|sqm|%|metres|square|ratio|height|width|setback)'
    LIMIT 10
''')

sepp_samples = cursor.fetchall()
for i, (text, ref, section) in enumerate(sepp_samples, 1):
    print(f'{i}. REF: {ref}')
    print(f'   SECTION: {section}')
    print(f'   TEXT: {text[:200]}...' if len(text) > 200 else f'   TEXT: {text}')
    print()

print('\n=== QUANTITATIVE EXTRACTION PATTERNS ===')
# Test regex patterns for common SEPP requirements
patterns = {
    'lot_size': r'(\d+(?:\.\d+)?)\s*(?:square\s*metres?|sqm|m²|m2)',
    'height': r'(\d+(?:\.\d+)?)\s*(?:metres?|m)\s*(?:high|height|above)',
    'setback': r'(\d+(?:\.\d+)?)\s*(?:metres?|m)\s*(?:setback|from)',
    'percentage': r'(\d+(?:\.\d+)?)\s*(?:%|percent|per\s*cent)',
    'ratio': r'(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)',
    'area': r'(\d+(?:\.\d+)?)\s*(?:hectares?|ha|square\s*kilometres?|km²)'
}

print('Testing extraction patterns on sample SEPP provisions:')
for i, (text, ref, section) in enumerate(sepp_samples[:5], 1):
    print(f'\nSample {i}: {ref}')
    print(f'Text: {text[:100]}...')

    for pattern_name, pattern in patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            print(f'  {pattern_name}: {matches}')

print('\n=== NSW API INTEGRATION ANALYSIS ===')
print('Current NSW API data extraction points:')
print('1. Special Provisions layer → raw provision data')
print('2. BASIX Climate Zone → "Zone 17", "Zone 18", etc.')
print('3. SEPP identification → "SEPP (Housing) 2021", clause references')

print('\n=== CLIMATE ZONE → ENERGY/WATER TARGETS ===')
cursor.execute('''
    SELECT climate_zone, development_type,
           energy_reduction_target, water_reduction_target,
           thermal_comfort_rating
    FROM basix_provisions
    ORDER BY climate_zone, development_type
''')

basix_targets = cursor.fetchall()
print('BASIX climate zone mappings:')
for zone, dev_type, energy, water, thermal in basix_targets:
    print(f'  {zone} + {dev_type}: {energy}% energy, {water}% water, {thermal} stars')

print('\n=== TIER AUTHORITY ASSIGNMENTS ===')
cursor.execute('''
    SELECT provision_type, provision_category,
           default_tier_level, authority_level, requires_specialist
    FROM special_provisions_registry
    ORDER BY default_tier_level, authority_level DESC
''')

tier_assignments = cursor.fetchall()
print('Provision tier assignments:')
for prov_type, category, tier, authority, specialist in tier_assignments:
    specialist_flag = ' (SPECIALIST)' if specialist else ''
    print(f'  Tier {tier}: {prov_type} ({category}) - {authority}% authority{specialist_flag}')

conn.close()