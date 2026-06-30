"""
DQ-11: Heritage Sub-Categorization for Marrickville

Categorizes 835 heritage provisions into:
- control: Actionable C1, C2, etc. provisions
- character: HCA-specific character statements
- descriptive: Background/historical content

Also tags:
- v2_heritage_element[]: roof, verandah, window, fence, garden, etc.
- v2_heritage_hca: hca_1, hca_2, etc. (Marrickville uses numbered HCAs)

Uses OpenAI API for reliable categorization.
"""

import os
import json
import psycopg2
from dotenv import load_dotenv
from openai import OpenAI
import time

load_dotenv()

# Database connection
DB_URL = 'postgresql://postgres@127.0.0.1:5432/nsw_planning'

# OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Valid values
HERITAGE_TYPES = ['control', 'character', 'descriptive']
HERITAGE_ELEMENTS = ['roof', 'verandah', 'window', 'door', 'fence', 'garden',
                     'facade', 'chimney', 'infill', 'car_parking', 'demolition',
                     'interior', 'materials', 'setback', 'scale', 'general']

# Marrickville HCAs (numbered 1-35)
HERITAGE_HCAS = [f'hca_{i}' for i in range(1, 36)]

CATEGORIZATION_PROMPT = """Categorize this heritage DCP provision from Marrickville Council (Part 8 Heritage).

PROVISION TEXT:
{text}

Return ONLY valid JSON (no markdown, no explanation):
{{
  "heritage_type": "control" | "character" | "descriptive",
  "heritage_element": ["element1", "element2"] or [],
  "heritage_hca": "hca_N" | null
}}

DEFINITIONS:
- "control": Actionable requirement. Starts with C1/C2/O1 etc, OR contains imperative verbs (Retain, Ensure, Minimise, Maintain) with specific requirements
- "character": Describes a SPECIFIC HCA's significance, history, key characteristics, building rankings, or area description. Must reference a specific HCA by number.
- "descriptive": General definitions, principles, style descriptions, historical background NOT specific to one HCA

ELEMENTS (only include if provision specifically addresses):
roof, verandah, window, door, fence, garden, facade, chimney, infill, car_parking, demolition, interior, materials, setback, scale, general

HCA FORMAT: Use "hca_N" where N is the HCA number (1-35). Return null if not area-specific.
Examples: hca_1 (Abergeldie Estate), hca_2 (King Street/Enmore Road), hca_10 (Camperdown Park), etc."""


def categorize_provision(text):
    """Use OpenAI to categorize a provision."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a heritage planning expert categorizing DCP provisions. Return ONLY valid JSON."},
                {"role": "user", "content": CATEGORIZATION_PROMPT.format(text=text[:2000])}
            ],
            temperature=0.1,
            max_tokens=200
        )

        result_text = response.choices[0].message.content.strip()

        # Clean up response (remove markdown if present)
        if result_text.startswith('```'):
            result_text = result_text.split('\n', 1)[1]
            result_text = result_text.rsplit('```', 1)[0]

        result = json.loads(result_text)

        # Validate and normalize
        heritage_type = result.get('heritage_type', 'descriptive')
        if heritage_type not in HERITAGE_TYPES:
            heritage_type = 'descriptive'

        heritage_element = result.get('heritage_element', [])
        if isinstance(heritage_element, str):
            heritage_element = [heritage_element]
        heritage_element = [e for e in heritage_element if e in HERITAGE_ELEMENTS]

        heritage_hca = result.get('heritage_hca')
        if heritage_hca and heritage_hca not in HERITAGE_HCAS:
            # Try to extract number
            import re
            match = re.search(r'(\d+)', str(heritage_hca))
            if match:
                num = int(match.group(1))
                if 1 <= num <= 35:
                    heritage_hca = f'hca_{num}'
                else:
                    heritage_hca = None
            else:
                heritage_hca = None

        return {
            'heritage_type': heritage_type,
            'heritage_element': heritage_element,
            'heritage_hca': heritage_hca
        }

    except Exception as e:
        print(f"Error categorizing: {e}")
        return {
            'heritage_type': 'descriptive',
            'heritage_element': [],
            'heritage_hca': None
        }


def get_heritage_provisions():
    """Get all Marrickville heritage provisions needing categorization."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute('''
        SELECT id, provision_text
        FROM regulatory_provisions
        WHERE document_id ILIKE '%marrickville%'
        AND v2_topic = 'Heritage'
        AND v2_heritage_type IS NULL
        ORDER BY id
    ''')

    provisions = cur.fetchall()
    cur.close()
    conn.close()

    return provisions


def update_provision(id, categorization):
    """Update a provision with categorization."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute('''
        UPDATE regulatory_provisions
        SET v2_heritage_type = %s,
            v2_heritage_element = %s,
            v2_heritage_hca = %s
        WHERE id = %s
    ''', (
        categorization['heritage_type'],
        categorization['heritage_element'],
        categorization['heritage_hca'],
        id
    ))

    conn.commit()
    cur.close()
    conn.close()


def run_categorization(batch_size=50, delay=0.3):
    """Run categorization on all uncategorized heritage provisions."""

    # Get provisions to categorize
    provisions = get_heritage_provisions()
    total = len(provisions)
    print(f"\nFound {total} Marrickville heritage provisions to categorize")

    if total == 0:
        print("All provisions already categorized!")
        return

    # Categorize in batches
    stats = {'control': 0, 'character': 0, 'descriptive': 0}

    for i, (id, text) in enumerate(provisions):
        if i > 0 and i % 50 == 0:
            print(f"\nProgress: {i}/{total} ({i*100//total}%)")
            print(f"Stats so far: {stats}")

        # Categorize
        result = categorize_provision(text)

        # Update database
        update_provision(id, result)

        # Track stats
        stats[result['heritage_type']] += 1

        # Rate limiting
        time.sleep(delay)

    print(f"\n=== COMPLETE ===")
    print(f"Total: {total}")
    print(f"Controls: {stats['control']}")
    print(f"Character: {stats['character']}")
    print(f"Descriptive: {stats['descriptive']}")


def verify_results():
    """Verify categorization results."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    print("\n=== MARRICKVILLE HERITAGE VERIFICATION ===")

    # Type distribution
    cur.execute('''
        SELECT v2_heritage_type, COUNT(*)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%marrickville%'
        AND v2_topic = 'Heritage'
        GROUP BY v2_heritage_type
        ORDER BY COUNT(*) DESC
    ''')
    print("\nBy type:")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]}")

    # Element distribution
    cur.execute('''
        SELECT unnest(v2_heritage_element) as elem, COUNT(*)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%marrickville%'
        AND v2_topic = 'Heritage'
        AND v2_heritage_type = 'control'
        GROUP BY elem
        ORDER BY COUNT(*) DESC
    ''')
    print("\nControl elements:")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]}")

    # HCA distribution
    cur.execute('''
        SELECT v2_heritage_hca, COUNT(*)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%marrickville%'
        AND v2_topic = 'Heritage'
        AND v2_heritage_hca IS NOT NULL
        GROUP BY v2_heritage_hca
        ORDER BY v2_heritage_hca
    ''')
    print("\nBy HCA:")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]}")

    # Sample controls
    cur.execute('''
        SELECT id, LEFT(provision_text, 100), v2_heritage_element
        FROM regulatory_provisions
        WHERE document_id ILIKE '%marrickville%'
        AND v2_heritage_type = 'control'
        LIMIT 5
    ''')
    print("\nSample controls:")
    for r in cur.fetchall():
        print(f"  [{r[0]}] {r[1]}... | elements: {r[2]}")

    cur.close()
    conn.close()


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--verify':
        verify_results()
    else:
        print("DQ-11: Marrickville Heritage Sub-Categorization")
        print("=" * 50)
        run_categorization()
        verify_results()
