"""
DQ-12: Building Form Tagging for Ashfield

Tags 200 Building Form provisions by BUILDING TYPE:
- secondary_dwelling, multi_dwelling, residential_flat
- child_care, boarding_house, neighbourhood_shop, etc.

Uses OpenAI API for reliable categorization.
Stores in v2_heritage_element field (array).
"""

import os
import json
import psycopg2
from dotenv import load_dotenv
from openai import OpenAI
import time
import argparse

load_dotenv()

# Database connection - Supabase
DB_CONFIG = {
    'host': 'aws-1-ap-southeast-2.pooler.supabase.com',
    'database': 'postgres',
    'user': 'postgres.llzdrxywpziewrzudwhj',
    'password': 'eDDIYq8ottiaO9ll',
    'port': 5432,
    'sslmode': 'require'
}

# OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Valid building types
BUILDING_TYPES = [
    'secondary_dwelling',
    'multi_dwelling',
    'residential_flat',
    'boarding_house',
    'child_care',
    'neighbourhood_shop',
    'mixed_use',
    'commercial',
    'industrial',
    'all_residential',  # applies to all residential types
    'all_development',  # applies to all development
]

# Valid provision types
PROVISION_TYPES = ['control', 'guidance', 'boilerplate']

CATEGORIZATION_PROMPT = """Categorize this Building Form DCP provision from Ashfield Council.

PROVISION TEXT:
{text}

Return ONLY valid JSON (no markdown, no explanation):
{{
  "type": "control" | "guidance" | "boilerplate",
  "building_types": ["type1", "type2"] or []
}}

DEFINITIONS FOR TYPE:
- "control": Specific requirement with numbers/standards (e.g., "minimum 6m setback", "maximum 9m height", "must provide")
- "guidance": Performance criteria, design principles, character descriptions, "should" statements
- "boilerplate": DCP structure explanation, "Design Solutions provide a guide", "Using this Guideline", application scope lists

BUILDING TYPES (which development types does this provision apply to?):
- secondary_dwelling: granny flats, secondary dwellings
- multi_dwelling: townhouses, villas, multi dwelling housing
- residential_flat: apartment buildings, residential flat buildings
- boarding_house: boarding houses, student accommodation
- child_care: child care centres
- neighbourhood_shop: local shops, neighbourhood shops
- mixed_use: mixed use development
- commercial: commercial/retail development
- industrial: industrial, warehouse
- all_residential: applies to ALL residential types generally
- all_development: applies to ALL development types

If the provision is boilerplate or doesn't specify a building type, use empty array []."""


def categorize_provision(text):
    """Use OpenAI to categorize a provision."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a planning expert categorizing DCP Building Form provisions. Return ONLY valid JSON."},
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
        provision_type = result.get('type', 'boilerplate')
        if provision_type not in PROVISION_TYPES:
            provision_type = 'boilerplate'

        building_types = result.get('building_types', [])
        if isinstance(building_types, str):
            building_types = [building_types]
        building_types = [t for t in building_types if t in BUILDING_TYPES]

        return {
            'type': provision_type,
            'building_types': building_types
        }

    except Exception as e:
        print(f"Error categorizing: {e}")
        return {
            'type': 'boilerplate',
            'building_types': []
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of provisions to process')
    parser.add_argument('--force', action='store_true', help='Re-tag all provisions, not just untagged')
    args = parser.parse_args()

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("=" * 60)
    print("DQ-12: Building Form Type Tagging")
    print("=" * 60)

    # Get Building Form provisions
    if args.force:
        cur.execute("""
            SELECT id, provision_text
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Ashfield%'
            AND v2_topic = 'Building Form'
            ORDER BY id
        """)
    else:
        cur.execute("""
            SELECT id, provision_text
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Ashfield%'
            AND v2_topic = 'Building Form'
            AND (v2_heritage_element IS NULL OR array_length(v2_heritage_element, 1) IS NULL)
            ORDER BY id
        """)
    provisions = cur.fetchall()

    if args.limit:
        provisions = provisions[:args.limit]

    print(f"\nFound {len(provisions)} provisions to tag")

    if args.dry_run:
        print("\n[DRY RUN] Would process these provisions:")
        for i, (id, text) in enumerate(provisions[:5]):
            print(f"  {i+1}. ID {id}: {text[:80]}...")
        if len(provisions) > 5:
            print(f"  ... and {len(provisions) - 5} more")
        return

    # Process each provision
    processed = 0
    errors = 0
    type_counts = {'control': 0, 'guidance': 0, 'boilerplate': 0}
    building_type_counts = {}

    for id, text in provisions:
        try:
            result = categorize_provision(text)

            # Update database - using v2_heritage_element for building_types and v2_heritage_type
            cur.execute("""
                UPDATE regulatory_provisions
                SET v2_heritage_element = %s,
                    v2_heritage_type = %s
                WHERE id = %s
            """, (
                result['building_types'] if result['building_types'] else None,
                result['type'],
                id
            ))
            conn.commit()

            type_counts[result['type']] = type_counts.get(result['type'], 0) + 1
            for bt in result['building_types']:
                building_type_counts[bt] = building_type_counts.get(bt, 0) + 1

            processed += 1
            if processed % 10 == 0:
                print(f"  Processed {processed}/{len(provisions)}...")

            # Rate limit
            time.sleep(0.1)

        except Exception as e:
            print(f"Error processing ID {id}: {e}")
            errors += 1

    print(f"\n{'=' * 60}")
    print("RESULTS")
    print('=' * 60)
    print(f"Processed: {processed}")
    print(f"Errors: {errors}")
    print(f"\nBy type:")
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")
    print(f"\nBy building type:")
    for bt, c in sorted(building_type_counts.items(), key=lambda x: -x[1]):
        print(f"  {bt}: {c}")

    conn.close()


if __name__ == '__main__':
    main()
