import json
import re

# Search through the verified LEP output for clause 4.3 and 4.4
lep_files = [
    "langextract_verified_output/Inner West Local Environmental Plan 2022 - NSW Legislation - Section 1_verified.json",
    "langextract_verified_output/Inner West Local Environmental Plan 2022 - NSW Legislation-51-100_verified.json",
    "langextract_verified_output/Inner West Local Environmental Plan 2022 - NSW Legislation-101-150_verified.json"
]

print("=== SEARCHING VERIFIED LEP OUTPUT FOR CLAUSE 4.3 AND 4.4 ===")

for file_path in lep_files:
    try:
        print(f"\n--- Checking: {file_path} ---")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Search through all sections
        sections_found = 0
        for section in data.get('sections', []):
            section_num = section.get('section_number', '')
            section_title = section.get('section_title', '')
            text = section.get('text', '')

            # Look for clause 4.3 or 4.4
            if ('4.3' in section_num or '4.4' in section_num or
                'floor space ratio' in section_title.lower() or
                'height of building' in section_title.lower() or
                'floor space ratio' in text.lower()[:200]):

                sections_found += 1
                print(f"\n*** FOUND SECTION {section_num}: {section_title} ***")
                print(f"Text length: {len(text)} characters")
                print(f"First 500 chars: {text[:500]}")
                if len(text) > 500:
                    print(f"CONTINUES... Total length: {len(text)}")
                    print(f"Last 200 chars: ...{text[-200:]}")
                print("-" * 80)

        print(f"Found {sections_found} relevant sections in this file")

    except Exception as e:
        print(f"Error reading {file_path}: {e}")

print("\n=== SUMMARY ===")
print("Search completed for clauses 4.3 and 4.4 in verified LEP output files.")