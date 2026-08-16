"""Check full Ashfield sample across ID range to find Part patterns."""

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

# Get ALL Ashfield provisions ordered by ID
cur.execute("""
    SELECT id, v2_dcp_part, provision_text, pdf_page
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Ashfield%'
      AND v2_dcp_layer = 'precinct'
      AND v2_is_actionable = true
    ORDER BY id;
""")

provisions = cur.fetchall()
print(f"Total Ashfield precinct provisions: {len(provisions)}\n")

# Try to find Part mentions in text
part_mentions = {}
for id, part, text, pdf_page in provisions:
    if text:
        # Look for "Part X" in text
        matches = re.findall(r'Part\s+(\d+)', text, re.IGNORECASE)
        if matches:
            part_num = matches[0]
            if part_num not in part_mentions:
                part_mentions[part_num] = []
            part_mentions[part_num].append((id, pdf_page, text[:100]))

if part_mentions:
    print("Provisions mentioning 'Part X' in text:")
    for part_num in sorted(part_mentions.keys(), key=int):
        samples = part_mentions[part_num][:3]  # First 3 samples
        print(f"\nPart {part_num} ({len(part_mentions[part_num])} mentions):")
        for id, pdf_page, text in samples:
            print(f"  ID {id} (page {pdf_page}): {text}...")
else:
    print("No 'Part X' mentions found in provision texts.")

# Check if provisions are grouped by ID/pdf_page ranges
print("\n\nProvision ID and PDF page ranges:")
print(f"First provision: ID {provisions[0][0]}, page {provisions[0][3]}")
print(f"Last provision: ID {provisions[-1][0]}, page {provisions[-1][3]}")

# Sample provisions across the range (every 10th)
print("\n\nProvisions sampled every 10th:")
for i in range(0, len(provisions), 10):
    id, part, text, pdf_page = provisions[i]
    text_preview = text[:80] if text else "None"
    print(f"{i:3d}. ID {id:6d}, page {pdf_page:4d}: {text_preview}...")

cur.close()
conn.close()
