"""
Tag v2_heritage_type for ALL heritage provisions in Supabase
Runs on Marrickville (549), Ashfield (1055), Leichhardt heritage provisions

Categorizes into:
- control: Actionable C1/C2/O1 provisions with requirements
- character: HCA-specific character statements
- descriptive: Background/historical/policy content

Uses OpenAI GPT-4o-mini for categorization
"""

import os
import json
import psycopg2
from dotenv import load_dotenv
from openai import OpenAI
import time

load_dotenv()

# SUPABASE PRODUCTION
DB_URL = os.getenv('DATABASE_URL')  # From .env file

# OpenAI client - explicitly get key from env
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in .env file")
print(f"Using OpenAI API key: {api_key[:10]}...")
client = OpenAI(api_key=api_key)

CATEGORIZATION_PROMPT = """Categorize this heritage DCP provision.

PROVISION TEXT:
{text}

Return ONLY valid JSON (no markdown):
{{
  "heritage_type": "control" | "character" | "descriptive"
}}

DEFINITIONS:
- "control": Actionable requirement. Starts with C1/C2/O1, OR contains imperative verbs (Retain, Ensure, Minimise, Maintain, Must) with specific requirements
- "character": Describes a SPECIFIC HCA's significance, history, key characteristics, building rankings. References specific HCA/area.
- "descriptive": General definitions, principles, style descriptions, policy statements NOT specific to one HCA

EXAMPLES:
Control: "C1 Roof pitch minimum 25° for heritage dwellings"
Control: "New additions must be setback from primary street frontage"
Character: "The Cardigan Street HCA is characterized by Victorian terraces with slate roofs"
Descriptive: "Heritage conservation aims to protect items of local significance"
"""


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
            max_tokens=50
        )

        result_text = response.choices[0].message.content.strip()

        # Clean up markdown
        if result_text.startswith('```'):
            result_text = result_text.split('\n', 1)[1].rsplit('```', 1)[0]

        result = json.loads(result_text)
        heritage_type = result.get('heritage_type', 'descriptive')

        if heritage_type not in ['control', 'character', 'descriptive']:
            heritage_type = 'descriptive'

        return heritage_type

    except Exception as e:
        print(f"Error categorizing: {e}")
        return 'descriptive'


def get_heritage_provisions():
    """Get all heritage provisions needing categorization."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Get ALL heritage provisions (re-tag everything)
    cur.execute('''
        SELECT id, provision_text, document_id
        FROM regulatory_provisions
        WHERE v2_marker = 'heritage'
        ORDER BY document_id, id
    ''')

    provisions = cur.fetchall()
    cur.close()
    conn.close()

    return provisions


def update_provision(id, heritage_type):
    """Update a provision with categorization."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute('''
        UPDATE regulatory_provisions
        SET v2_heritage_type = %s
        WHERE id = %s
    ''', (heritage_type, id))

    conn.commit()
    cur.close()
    conn.close()


def run_categorization():
    """Run categorization on all heritage provisions."""

    provisions = get_heritage_provisions()
    total = len(provisions)
    print(f"\nFound {total} heritage provisions to categorize")

    if total == 0:
        print("All provisions already categorized!")
        return

    stats = {'control': 0, 'character': 0, 'descriptive': 0}
    council_stats = {}

    for i, (id, text, doc_id) in enumerate(provisions):
        if i > 0 and i % 50 == 0:
            print(f"\nProgress: {i}/{total} ({i*100//total}%)")
            print(f"Stats so far: {stats}")

        # Categorize
        heritage_type = categorize_provision(text)

        # Update database
        update_provision(id, heritage_type)

        # Track stats
        stats[heritage_type] += 1

        # Track by council
        council = 'Unknown'
        if 'Marrickville' in doc_id:
            council = 'Marrickville'
        elif 'Ashfield' in doc_id:
            council = 'Ashfield'
        elif 'Leichhardt' in doc_id:
            council = 'Leichhardt'

        if council not in council_stats:
            council_stats[council] = {'control': 0, 'character': 0, 'descriptive': 0}
        council_stats[council][heritage_type] += 1

        # Rate limiting
        time.sleep(0.05)  # 20 requests/second (well under GPT-4o-mini limit)

    print(f"\n=== COMPLETE ===")
    print(f"Total: {total}")
    print(f"Controls: {stats['control']} ({stats['control']*100//total}%)")
    print(f"Character: {stats['character']} ({stats['character']*100//total}%)")
    print(f"Descriptive: {stats['descriptive']} ({stats['descriptive']*100//total}%)")

    print(f"\n=== BY COUNCIL ===")
    for council, council_stat in council_stats.items():
        total_council = sum(council_stat.values())
        print(f"\n{council} ({total_council} provisions):")
        print(f"  Controls: {council_stat['control']} ({council_stat['control']*100//total_council if total_council > 0 else 0}%)")
        print(f"  Character: {council_stat['character']} ({council_stat['character']*100//total_council if total_council > 0 else 0}%)")
        print(f"  Descriptive: {council_stat['descriptive']} ({council_stat['descriptive']*100//total_council if total_council > 0 else 0}%)")


def verify_results():
    """Verify categorization results."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    print("\n=== VERIFICATION ===")

    # Overall distribution
    cur.execute('''
        SELECT v2_heritage_type, COUNT(*)
        FROM regulatory_provisions
        WHERE v2_marker = 'heritage'
        GROUP BY v2_heritage_type
        ORDER BY COUNT(*) DESC
    ''')
    print("\nOverall distribution:")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]}")

    # By council
    cur.execute('''
        SELECT
            CASE
                WHEN document_id ILIKE '%Marrickville%' THEN 'Marrickville'
                WHEN document_id ILIKE '%Ashfield%' THEN 'Ashfield'
                WHEN document_id ILIKE '%Leichhardt%' THEN 'Leichhardt'
                ELSE 'Other'
            END as council,
            v2_heritage_type,
            COUNT(*)
        FROM regulatory_provisions
        WHERE v2_marker = 'heritage'
        GROUP BY council, v2_heritage_type
        ORDER BY council, COUNT(*) DESC
    ''')
    print("\nBy council:")
    for r in cur.fetchall():
        print(f"  {r[0]} - {r[1]}: {r[2]}")

    # Sample controls
    cur.execute('''
        SELECT id, LEFT(provision_text, 120), document_id
        FROM regulatory_provisions
        WHERE v2_heritage_type = 'control'
        LIMIT 5
    ''')
    print("\nSample controls:")
    for r in cur.fetchall():
        print(f"\n  [{r[0]}] {r[1]}...")
        print(f"  {r[2]}")

    cur.close()
    conn.close()


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--verify':
        verify_results()
    else:
        print("Heritage Type Tagging for Supabase Production")
        print("=" * 60)
        print("Starting categorization...")

        run_categorization()
        verify_results()
