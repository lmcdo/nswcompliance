"""
Audit all must/shall false negatives — classify each as:
  ARTIFACT  - reversed/corrupted Ashfield PDF text (should be cleaned, not fixed here)
  REAL_FN   - genuine binding control incorrectly marked non-actionable
  LEGIT     - legitimately excluded (objectives, TOC fragment, application text)
"""
import os, re, psycopg2
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Reversed-text artifact pattern — sequences of 4+ chars reversed
REVERSED_WORD_PATTERN = re.compile(r'\b[a-z]{4,}(?=[A-Z])|(?<=[a-z])[A-Z][a-z]{3,}\b')
REVERSED_SIGNALS = ['suoenallecsiM', 'retpahC', 'drazaH', 'doolF', 'ytiliboM', 'sseccA',
                    'noisividbuS', 'ngiseD', 'serutcurtS', 'gnisitrevdA', 'sngiS',
                    'ertneC', 'nwoT', 'senilediuG', 'tcnicerP', 'gnikraP', 'srodirroC',
                    'ytilibanicatsuS', 'egatireH', 'snoitcnuF', 'esruoC', 'ytisnedwoL']

OBJECTIVES_PATTERNS = ['objective', 'document information', 'purpose', 'application purpose',
                        'background', 'introduction', 'how to use', 'contents']
FRAGMENT_PATTERNS = [r'^#\s+\w+\-', r'^\s*[-•]\s*$', r'^Page \d+']
TABLE_SIGNALS = ['<table>', '<thead>', '<tr>', 'Performance Criteria', 'Performance Criteri']

def classify_provision(text, header):
    t = text or ''
    h = (header or '').lower()

    # Artifact check
    for sig in REVERSED_SIGNALS:
        if sig in t:
            return 'ARTIFACT'

    # Objectives/preamble header
    for pat in OBJECTIVES_PATTERNS:
        if pat in h:
            return 'LEGIT_HEADER'

    # Table-only content (no actual clause text)
    if any(s in t for s in TABLE_SIGNALS):
        # Could still have real text around the table
        stripped = re.sub(r'<[^>]+>', '', t)
        if len(stripped.strip()) < 80:
            return 'LEGIT_TABLE_ONLY'

    # Fragment / section heading only
    lines = [l.strip() for l in t.strip().splitlines() if l.strip()]
    real_lines = [l for l in lines if len(l) > 40]
    if len(real_lines) == 0:
        return 'LEGIT_FRAGMENT'

    # Contains must/shall in substantive sentence
    sentences = re.split(r'[.!?]', t)
    binding_sentences = [s for s in sentences if
                         re.search(r'\b(must|shall)\b', s, re.IGNORECASE) and
                         len(s.strip()) > 30]
    if binding_sentences:
        return 'REAL_FN'

    return 'LEGIT_OTHER'


cur.execute("""
    SELECT id, document_id, section_header, provision_text
    FROM regulatory_provisions
    WHERE (provision_text ILIKE '%must%' OR provision_text ILIKE '%shall%')
      AND v2_is_actionable = false
      AND document_id ILIKE '%DCP%'
      AND (section_header NOT ILIKE '%Objective%'
           OR section_header IS NULL)
      AND (section_header NOT ILIKE '%Document Information%'
           OR section_header IS NULL)
      AND (section_header NOT ILIKE '% Purpose%'
           OR section_header IS NULL)
    ORDER BY document_id, id
""")
rows = cur.fetchall()

results = {'REAL_FN': [], 'ARTIFACT': [], 'LEGIT_HEADER': [], 'LEGIT_FRAGMENT': [],
           'LEGIT_TABLE_ONLY': [], 'LEGIT_OTHER': []}

for row in rows:
    cat = classify_provision(row[3], row[2])
    results[cat].append(row)

print(f"Total audited: {len(rows)}")
print()
for cat, items in results.items():
    print(f"  {cat:20s}: {len(items)}")

print()
print("=== REAL FALSE NEGATIVES ===")
for r in results['REAL_FN']:
    print(f"  ID:{r[0]} | {r[1]}")
    print(f"    header: {r[2]}")
    sentences = re.split(r'[.!?]', r[3] or '')
    binding = [s.strip() for s in sentences if re.search(r'\b(must|shall)\b', s, re.IGNORECASE) and len(s.strip()) > 30]
    for b in binding[:2]:
        print(f"    >> {b[:180]}")
    print()

real_fn_ids = [r[0] for r in results['REAL_FN']]
print(f"\nIDs to fix: {real_fn_ids}")

cur.close()
conn.close()
