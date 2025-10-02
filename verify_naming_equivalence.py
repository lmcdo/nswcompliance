#!/usr/bin/env python3
"""
Verify the UI dropdown → Database naming equivalence
"""

# UI dropdown values
UI_VALUES = [
    'dwelling_house',
    'secondary_dwelling',
    'shop_top_housing',
    'multi_dwelling',
    'residential_flat',
    'boarding_house',
    'child_care',
    'commercial'
]

# Likely database/LEP equivalents
EQUIVALENCE_MAP = {
    'dwelling_house': 'dwelling house',           # spaces
    'secondary_dwelling': 'secondary dwelling',   # spaces
    'shop_top_housing': 'shop top housing',       # spaces
    'multi_dwelling': 'multi dwelling housing',   # spaces + "housing"
    'residential_flat': 'residential flat building', # spaces + "building"
    'boarding_house': 'boarding house',           # spaces
    'child_care': 'child care centre',            # spaces + "centre"
    'commercial': 'business premises'             # different term
}

print("=== UI → LEP Naming Equivalence ===\n")
print(f"{'UI Value':25} → {'LEP Term':30}")
print("-" * 60)

for ui_val, lep_term in EQUIVALENCE_MAP.items():
    # Convert
    ui_to_lep = ui_val.replace('_', ' ')
    match = '✓' if ui_to_lep in lep_term else '?'
    print(f"{ui_val:25} → {lep_term:30} {match}")

print("\n=== Conversion Pattern ===")
print("Simple conversion: underscore → space")
print("Exceptions:")
print("  - multi_dwelling → multi dwelling HOUSING")
print("  - residential_flat → residential flat BUILDING")
print("  - child_care → child care CENTRE")
print("  - commercial → business premises (DIFFERENT)")
