import os
import re
import glob

print('=== Extracting Precinct Boundary Descriptions ===\n')

# Find all Marrickville precinct markdown files
precinct_files = glob.glob('output/Marrickville DCP 2011 - 9 */auto/*.md')

print(f'Found {len(precinct_files)} precinct markdown files\n')

boundaries = {}

for file_path in sorted(precinct_files):
    # Extract precinct number from filename
    filename = os.path.basename(file_path)

    # Parse precinct number (e.g., "9 10" -> "10_", "9 1" -> "1_")
    match = re.search(r'9 (\d+)', filename)
    if not match:
        continue

    precinct_num = match.group(1) + '_'

    # Read the markdown file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract precinct name from header
    name_match = re.search(r'#+ 9\.\d+\s+(.+?)(?:\(Precinct \d+\))?$', content, re.MULTILINE)
    precinct_name = name_match.group(1).strip() if name_match else 'Unknown'

    # Find boundary description - usually in "Existing character" section
    # Look for patterns like "bounded by", "It is bounded", etc.
    boundary_patterns = [
        r'(?:is )?bounded by (.+?)\.(?:\s|$)',
        r'bounded to the (.+?)\.(?:\s|$)',
        r'boundaries are (.+?)\.(?:\s|$)',
        r'extent of (?:the )?(?:precinct|area) is (.+?)\.(?:\s|$)',
    ]

    boundary_text = None
    for pattern in boundary_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            boundary_text = match.group(1).strip()
            break

    # Also extract full "Existing character" section for context
    char_match = re.search(r'# 9\.\d+\.1 Existing character\s+(.+?)(?=\n# 9\.\d+\.2|$)', content, re.DOTALL)
    existing_char = char_match.group(1).strip()[:500] if char_match else ''

    boundaries[precinct_num] = {
        'name': precinct_name,
        'boundary_text': boundary_text,
        'existing_char_excerpt': existing_char,
        'file': file_path
    }

    print(f'Precinct {precinct_num}: {precinct_name}')
    if boundary_text:
        print(f'  Boundary: {boundary_text}')
    else:
        print(f'  Boundary: NOT FOUND (check manually)')
    print()

# Save to file
import json
with open('precinct_boundaries_extracted.json', 'w', encoding='utf-8') as f:
    json.dump(boundaries, f, indent=2, ensure_ascii=False)

print(f'\nSaved {len(boundaries)} precinct boundaries to precinct_boundaries_extracted.json')
print('\nNext step: Parse street names and geocode them to create boundary polygons')
