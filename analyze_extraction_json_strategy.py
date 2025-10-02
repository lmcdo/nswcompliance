import json
from pathlib import Path

# Load the large extraction file
extraction_path = Path("public/regulatory-data/leichhardt_semantic_extraction.json")
with open(extraction_path) as f:
    data = json.load(f)

print("=== Leichhardt Semantic Extraction Structure ===\n")
print(f"Top-level keys: {list(data.keys())}\n")

# Check validation data
if 'validation' in data:
    validation = data['validation']
    print(f"Total potential rules: {validation.get('total_potential_rules')}")
    print(f"Total extracted rules: {validation.get('total_extracted_rules')}\n")

    print(f"Potential rules by type:")
    for rule_type, rules in validation.get('potential_rules_by_type', {}).items():
        print(f"  - {rule_type}: {len(rules)} rules")
        if rules and len(rules) > 0:
            print(f"    Sample: value={rules[0].get('value')}, context length={len(rules[0].get('context', ''))}")

# Check if there are enhanced_rules
if 'enhanced_rules' in data:
    print(f"\nEnhanced rules: {data['total_enhanced_rules']}")
    print(f"High confidence: {data['high_confidence_rules']}")

# Check langextract_extractions
print(f"\nLangextract extractions: {data.get('langextract_extractions', 0)}")
print(f"Autoschemakg triples: {data.get('autoschemakg_triples', 0)}")

print("\n\n=== How This Should Work ===\n")
print("For query: R2 zone + dwelling_house")
print("\n1. Search validation.potential_rules_by_type for:")
print("   - 'front_setback' rules")
print("   - 'rear_setback' rules")
print("   - 'side_setback' rules")
print("   - 'height' rules")
print("   - 'parking' rules")

print("\n2. Filter rules by:")
print("   - Context contains 'R2' or 'residential'")
print("   - Context contains 'dwelling' or 'house'")
print("   - Has numeric value extracted")

print("\n3. Return top 10-15 most relevant rules ranked by:")
print("   - Has explicit zone reference")
print("   - Has explicit development type")
print("   - Has numeric value")

print("\n\n=== Strategy: Use JSON Files Directly ===\n")
print("Instead of querying database with WHERE clauses,")
print("create a service that:")
print("  1. Loads extraction JSON files (cached)")
print("  2. Searches rules by type (setback, height, etc.)")
print("  3. Filters by zone + development type in context")
print("  4. Returns provision IDs + values")
print("  5. Frontend fetches full text from database")