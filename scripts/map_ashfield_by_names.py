"""Map Ashfield provisions to Parts by matching precinct names in text."""

import os, psycopg2, re
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')

conn = psycopg2.connect(
    host=os.getenv('PGHOST'),
    database=os.getenv('PGDATABASE'),
    user=os.getenv('PGUSER'),
    password=os.getenv('PGPASSWORD'),
    port=os.getenv('PGPORT')
)
cur = conn.cursor()

# Precinct names from dcp_precinct_boundaries
ASHFIELD_PRECINCTS = {
    'Part 1': ['Ashfield Town Centre', 'Town Centre'],
    'Part 2': ['Ashfield East'],
    'Part 3': ['Ashfield West'],
    'Part 4': ['Croydon Urban Village', 'Croydon'],
    'Part 6': ['Enterprise Zone', 'Parramatta Road', 'B6', 'Parramatta Rd'],
    'Part 7': ['Hurlstone Park'],
    'Part 8': ['Summer Hill Urban Village', 'SummerHill'],
    'Part 9': ['Summer Hill Flour Mill', 'Flour Mill'],
    'Part 10': ['Edwards Street', 'B4 Zone'],
    'Part 12': ['55 to 63 Smith St', 'Smith Street', 'Smith St'],
    'Part 13': ['120C Old Canterbury', 'Canterbury Road', 'Canterbury Rd'],
}

# Get all Ashfield provisions
cur.execute("""
    SELECT id, provision_text, pdf_page
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Ashfield%'
      AND v2_dcp_layer = 'precinct'
      AND v2_is_actionable = true
    ORDER BY pdf_page, id;
""")

provisions = cur.fetchall()
print(f"Total Ashfield provisions: {len(provisions)}\n")

# Try to match each provision to a Part based on text content
matches = {part: [] for part in ASHFIELD_PRECINCTS.keys()}
unmatched = []

for id, text, pdf_page in provisions:
    text_lower = text.lower() if text else ""
    matched = False

    for part, keywords in ASHFIELD_PRECINCTS.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                matches[part].append((id, pdf_page, text[:100]))
                matched = True
                break
        if matched:
            break

    if not matched:
        unmatched.append((id, pdf_page, text[:100] if text else "None"))

# Print results
print("Provisions matched to Parts:")
for part in sorted(matches.keys(), key=lambda x: int(re.search(r'\d+', x).group())):
    if matches[part]:
        print(f"\n{part} ({len(matches[part])} provisions):")
        for id, pdf_page, text in matches[part][:3]:  # First 3 samples
            print(f"  ID {id} (page {pdf_page}): {text}...")

print(f"\n\nUnmatched provisions ({len(unmatched)} total):")
for id, pdf_page, text in unmatched[:10]:  # First 10 samples
    print(f"  ID {id} (page {pdf_page}): {text}...")

# Print page range for unmatched
if unmatched:
    pages = [p for _, p, _ in unmatched if p]
    print(f"\nUnmatched page range: {min(pages)} - {max(pages)}")

cur.close()
conn.close()
