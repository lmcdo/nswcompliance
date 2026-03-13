#!/usr/bin/env python3
"""
Strip reversed OCR sidebar labels from Ku-ring-gai provision text.

KRG PDFs have rotated section labels (e.g. SUBDIVISION, PARKING, ACCESS) printed
sideways in the page margin. pdfplumber extracts them as isolated uppercase lines
mixed into the provision text. They are noise — not content.

Reversed tokens identified:
  NOISIVIDBUS   = SUBDIVISION
  NOITADILOSNOC = CONSOLIDATION
  SLORTNOC      = CONTROLS
  LARENEG       = GENERAL
  GNIKRAP       = PARKING
  SSECCA        = ACCESS
  NGISED        = DESIGN
  DNA           = AND
  ROF           = FOR (skip — too short, legit uses exist)
  ERUTCURTS     = STRUCTURE
  TNEMPOLEVD    = DEVELOPMENT (partial)

Strategy: remove lines that are ONLY these reversed tokens (standalone lines).
Safe because real English content won't be entirely these tokens.
"""
import os, sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# These reversed tokens appear as isolated lines — safe to remove as standalone
REVERSED_TOKENS = {
    'NOISIVIDBUS', 'NOITADILOSNOC', 'SLORTNOC', 'LARENEG',
    'GNIKRAP', 'SSECCA', 'NGISED', 'DNA', 'ROF', 'ERUTCURTS',
    'TNEMPOLEVD', 'TNEMPOLEVED', 'LAICREMMOS', 'LAITNEDISER',
    'GNIDLIUB', 'TNEMEGANAM', 'TNEMSSESSA', 'YTITNEDI',
    'NOITCETORP', 'NOITAVRESERP', 'EGATIREH',
    # Signage chapter sidebar labels (identified 2026-03-14)
    'GNISITREVDA',  # ADVERTISING
    'EGANGIS',      # SIGNAGE
    '&',            # standalone ampersand from "DESIGN & ADVERTISING" label
    # Standalone page header lines
    'Ku-ring-gai Development Control Plan',
}

# Also strip isolated part-code lines like "3A", "6B", "8A" that are just page headers
PART_CODE_RE = re.compile(r'^[0-9]+[A-Z]$')

def clean_text(text: str) -> str:
    if not text:
        return text
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Remove standalone reversed tokens
        if stripped in REVERSED_TOKENS:
            continue
        # Remove isolated part codes (e.g. "3A", "6B") that are margin labels
        if PART_CODE_RE.match(stripped):
            continue
        cleaned.append(line)
    # Collapse 3+ consecutive blank lines to 2
    result = re.sub(r'\n{3,}', '\n\n', '\n'.join(cleaned))
    return result.strip()


conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

cur.execute("""
    SELECT id, provision_text FROM regulatory_provisions
    WHERE source_council = 'ku_ring_gai' AND is_current = true
""")
rows = cur.fetchall()
print(f"Checking {len(rows)} provisions...")

updates = []
for pid, text in rows:
    cleaned = clean_text(text)
    if cleaned != (text or '').strip():
        updates.append((cleaned, pid))

print(f"Provisions needing cleanup: {len(updates)}")

for new_text, pid in updates:
    cur.execute("UPDATE regulatory_provisions SET provision_text = %s WHERE id = %s", (new_text, pid))

conn.commit()
print(f"Applied {len(updates)} text cleanups.")
cur.close()
conn.close()
