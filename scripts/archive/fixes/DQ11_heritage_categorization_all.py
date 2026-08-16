"""
DQ-11 FIX: Heritage Sub-Categorization for ALL Ashfield Heritage Provisions

Previous script only processed v2_dcp_layer='condition' provisions.
This script processes ALL v2_topic='heritage' provisions regardless of layer.

Categorizes into:
- control: Actionable requirements (C1, C2, imperative verbs)
- character: HCA-specific character statements
- descriptive: General definitions, principles, background

Uses OpenAI API for reliable categorization.
"""

import os
import json
import psycopg2
from dotenv import load_dotenv
from openai import OpenAI
import time

load_dotenv()

# Database connection - use environment variables
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'aws-1-ap-southeast-2.pooler.supabase.com'),
    'database': os.getenv('DB_NAME', 'postgres'),
    'user': os.getenv('DB_USER', 'postgres.llzdrxywpziewrzudwhj'),
    'password': os.getenv('DB_PASSWORD', 'eDDIYq8ottiaO9ll'),
    'port': os.getenv('DB_PORT', '5432'),
    'sslmode': 'require'
}

# OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Valid values
HERITAGE_TYPES = ['control', 'character', 'descriptive']
HERITAGE_ELEMENTS = ['roof', 'verandah', 'window', 'door', 'fence', 'garden',
                     'facade', 'chimney', 'infill', 'car_parking', 'demolition',
                     'interior', 'materials', 'setback', 'scale', 'general']

CATEGORIZATION_PROMPT = """Categorize this heritage DCP provision from Ashfield Council.

PROVISION TEXT:
{text}

Return ONLY valid JSON (no markdown, no explanation):
{{
  "heritage_type": "control" | "character" | "descriptive",
  "heritage_element": ["element1", "element2"] or []
}}

DEFINITIONS:
- "control": Actionable requirement. Contains imperative verbs (Retain, Ensure, Minimise, Maintain, Must, Should, Avoid) with specific requirements. Tells you what TO DO or NOT DO.
- "character": Describes significance, history, key characteristics of a specific area or building type. Explains WHY something is important.
- "descriptive": General definitions, principles, style descriptions. Provides BACKGROUND information.

ELEMENTS (only if provision specifically addresses):
roof, verandah, window, door, fence, garden, facade, chimney, infill, car_parking, demolition, interior, materials, setback, scale, general

Examples:
- "Retain original verandah details" → control, [verandah]
- "The area is significant for its Victorian terraces" → character, []
- "Federation style is characterized by..." → descriptive, []"""


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(**DB_CONFIG)


def categorize_provision(text):
    """Use OpenAI to categorize a provision."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a heritage planning expert. Return ONLY valid JSON."},
                {"role": "user", "content": CATEGORIZATION_PROMPT.format(text=text[:2000])}
            ],
            temperature=0.1,
            max_tokens=150
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

        return {
            'heritage_type': heritage_type,
            'heritage_element': heritage_element
        }

    except Exception as e:
        print(f"  Error: {e}")
        return {
            'heritage_type': 'descriptive',
            'heritage_element': []
        }


def get_uncategorized_provisions():
    """Get ALL Ashfield heritage provisions that need categorization."""
    conn = get_db_connection()
    cur = conn.cursor()

    # Get ALL heritage provisions - NO layer filter!
    cur.execute('''
        SELECT id, provision_text, v2_dcp_layer, v2_heritage_hca
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Ashfield%'
        AND LOWER(v2_topic) = 'heritage'
        AND (v2_heritage_type IS NULL OR v2_heritage_type = '')
        ORDER BY id
    ''')

    provisions = cur.fetchall()
    cur.close()
    conn.close()

    return provisions


def get_total_heritage_count():
    """Get total count of Ashfield heritage provisions."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Ashfield%'
        AND LOWER(v2_topic) = 'heritage'
    ''')

    total = cur.fetchone()[0]
    cur.close()
    conn.close()

    return total


def update_provision(provision_id, categorization):
    """Update a provision with categorization."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        UPDATE regulatory_provisions
        SET v2_heritage_type = %s,
            v2_heritage_element = %s
        WHERE id = %s
    ''', (
        categorization['heritage_type'],
        categorization['heritage_element'],
        provision_id
    ))

    conn.commit()
    cur.close()
    conn.close()


def verify_coverage():
    """Verify all heritage provisions are categorized."""
    conn = get_db_connection()
    cur = conn.cursor()

    print("\n" + "=" * 60)
    print("COVERAGE VERIFICATION")
    print("=" * 60)

    # Total heritage provisions
    cur.execute('''
        SELECT COUNT(*) FROM regulatory_provisions
        WHERE document_id ILIKE '%Ashfield%'
        AND LOWER(v2_topic) = 'heritage'
    ''')
    total = cur.fetchone()[0]

    # Categorized provisions
    cur.execute('''
        SELECT COUNT(*) FROM regulatory_provisions
        WHERE document_id ILIKE '%Ashfield%'
        AND LOWER(v2_topic) = 'heritage'
        AND v2_heritage_type IS NOT NULL
    ''')
    categorized = cur.fetchone()[0]

    print(f"\nTotal heritage provisions: {total}")
    print(f"Categorized: {categorized}")
    print(f"Missing: {total - categorized}")
    print(f"Coverage: {categorized * 100 / total:.1f}%")

    # By type
    cur.execute('''
        SELECT v2_heritage_type, COUNT(*) as cnt
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Ashfield%'
        AND LOWER(v2_topic) = 'heritage'
        GROUP BY v2_heritage_type
        ORDER BY cnt DESC
    ''')

    print("\nBy type:")
    for row in cur.fetchall():
        pct = row[1] * 100 / total
        print(f"  {row[0] or 'NULL':15} {row[1]:4} ({pct:5.1f}%)")

    # By layer (to confirm we're covering all)
    cur.execute('''
        SELECT v2_dcp_layer,
               COUNT(*) as total,
               SUM(CASE WHEN v2_heritage_type IS NOT NULL THEN 1 ELSE 0 END) as tagged
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Ashfield%'
        AND LOWER(v2_topic) = 'heritage'
        GROUP BY v2_dcp_layer
        ORDER BY total DESC
    ''')

    print("\nBy layer (coverage check):")
    for row in cur.fetchall():
        layer, total_layer, tagged = row
        pct = tagged * 100 / total_layer if total_layer > 0 else 0
        status = "✅" if pct == 100 else "❌"
        print(f"  {status} {layer or 'NULL':15} {tagged}/{total_layer} ({pct:.0f}%)")

    cur.close()
    conn.close()

    return categorized == total


def run_categorization(batch_size=50, delay=0.3):
    """Run categorization on all uncategorized heritage provisions."""

    total_heritage = get_total_heritage_count()
    print(f"\nTotal Ashfield heritage provisions: {total_heritage}")

    provisions = get_uncategorized_provisions()
    to_process = len(provisions)

    print(f"Uncategorized provisions to process: {to_process}")

    if to_process == 0:
        print("\n✅ All provisions already categorized!")
        verify_coverage()
        return

    print(f"\nProcessing {to_process} provisions...")
    print("=" * 60)

    stats = {'control': 0, 'character': 0, 'descriptive': 0}
    errors = 0

    for i, (prov_id, text, layer, hca) in enumerate(provisions):
        # Progress update
        if i > 0 and i % 50 == 0:
            print(f"\nProgress: {i}/{to_process} ({i*100//to_process}%)")
            print(f"Stats: control={stats['control']}, character={stats['character']}, descriptive={stats['descriptive']}")

        # Categorize
        result = categorize_provision(text)

        # Update database
        try:
            update_provision(prov_id, result)
            stats[result['heritage_type']] += 1
        except Exception as e:
            print(f"  DB Error for {prov_id}: {e}")
            errors += 1

        # Rate limiting
        time.sleep(delay)

    print("\n" + "=" * 60)
    print("CATEGORIZATION COMPLETE")
    print("=" * 60)
    print(f"Processed: {to_process}")
    print(f"Errors: {errors}")
    print(f"\nResults:")
    print(f"  control:     {stats['control']}")
    print(f"  character:   {stats['character']}")
    print(f"  descriptive: {stats['descriptive']}")

    # Verify
    verify_coverage()


if __name__ == '__main__':
    import sys

    print("=" * 60)
    print("DQ-11 FIX: Heritage Categorization (ALL provisions)")
    print("=" * 60)

    if len(sys.argv) > 1 and sys.argv[1] == '--verify':
        verify_coverage()
    elif len(sys.argv) > 1 and sys.argv[1] == '--dry-run':
        provisions = get_uncategorized_provisions()
        print(f"\nWould process {len(provisions)} provisions")
        print("\nSample (first 5):")
        for prov_id, text, layer, hca in provisions[:5]:
            print(f"  [{prov_id}] layer={layer}, hca={hca}")
            print(f"      {text[:100]}...")
    else:
        run_categorization()
