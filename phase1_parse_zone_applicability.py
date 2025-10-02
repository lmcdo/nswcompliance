"""
Phase 1: Parse Zone Applicability from Provision Text
Objective: Handle NULL zones by inferring applicability from text and document type
"""

import psycopg2
import re
from typing import List, Dict, Set

def get_connection():
    return psycopg2.connect(
        host='localhost',
        database='nsw_planning',
        user='postgres',
        password='postgres',
        port=5432
    )


def extract_zone_mentions(provision_text: str) -> Set[str]:
    """
    Extract zone codes mentioned in provision text

    Zones: R1-R5, B1-B8, IN1-IN4, RE1-RE2, RU1-RU6, E1-E4, SP1-SP3, W1-W4
    """
    if not provision_text:
        return set()

    # Pattern for NSW standard zones
    zone_pattern = r'\b(R[1-5]|B[1-8]|IN[1-4]|RE[1-2]|RU[1-6]|E[1-4]|SP[1-3]|W[1-4])\b'
    zones = re.findall(zone_pattern, provision_text)

    return set(zones)


def check_universal_applicability(provision_text: str) -> bool:
    """
    Check if provision explicitly applies to all zones
    """
    if not provision_text:
        return False

    text_lower = provision_text.lower()

    universal_phrases = [
        'all zones',
        'any zone',
        'all land',
        'any land',
        'throughout the lga',
        'across all zones',
        'regardless of zone',
        'in all cases'
    ]

    return any(phrase in text_lower for phrase in universal_phrases)


def get_document_type_applicability(document_id: str) -> Dict:
    """
    Determine applicability based on document type
    """
    doc_lower = document_id.lower()

    # SEPP - State Environmental Planning Policy (state-wide)
    if 'sepp' in doc_lower or 'state_environmental' in doc_lower:
        return {
            'state_wide': True,
            'lga': None,
            'source': 'sepp_document'
        }

    # LEP - Local Environmental Plan (LGA-wide)
    if 'lep' in doc_lower or 'local_environmental' in doc_lower:
        lga = None
        if 'inner_west' in doc_lower or 'inner west' in doc_lower:
            lga = 'Inner West'
        elif 'canada_bay' in doc_lower or 'canada bay' in doc_lower:
            lga = 'Canada Bay'

        return {
            'state_wide': False,
            'lga': lga,
            'source': 'lep_document'
        }

    # DCP - Development Control Plan (LGA-wide, usually)
    if 'dcp' in doc_lower:
        lga = None
        if 'marrickville' in doc_lower:
            lga = 'Inner West'
        elif 'ashfield' in doc_lower:
            lga = 'Inner West'
        elif 'leichhardt' in doc_lower:
            lga = 'Inner West'
        elif 'inner_west' in doc_lower or 'inner west' in doc_lower:
            lga = 'Inner West'

        return {
            'state_wide': False,
            'lga': lga,
            'source': 'dcp_document'
        }

    return {
        'state_wide': False,
        'lga': None,
        'source': 'unknown'
    }


def determine_applicability(provision: Dict) -> List[Dict]:
    """
    Determine all applicable zones for a provision

    Returns list of applicability records to insert
    """
    prov_id = provision['id']
    prov_text = provision['provision_text']
    explicit_zone = provision['zone']
    document_id = provision['document_id']

    applicability_records = []

    # Case 1: Provision has explicit zone
    if explicit_zone:
        applicability_records.append({
            'provision_id': prov_id,
            'applies_to_zone': explicit_zone,
            'applies_to_all_zones': False,
            'applies_state_wide': False,
            'applies_to_lga': None,
            'excluded_zones': None,
            'applicability_source': 'explicit_zone',
            'confidence_score': 1.0,
            'notes': f'Explicit zone: {explicit_zone}'
        })
        return applicability_records

    # Case 2: Check if universal applicability
    if check_universal_applicability(prov_text):
        doc_info = get_document_type_applicability(document_id)
        applicability_records.append({
            'provision_id': prov_id,
            'applies_to_zone': None,
            'applies_to_all_zones': True,
            'applies_state_wide': doc_info['state_wide'],
            'applies_to_lga': doc_info['lga'],
            'excluded_zones': None,
            'applicability_source': 'text_all_zones',
            'confidence_score': 0.9,
            'notes': 'Provision text indicates universal applicability'
        })
        return applicability_records

    # Case 3: Extract zone mentions from text
    mentioned_zones = extract_zone_mentions(prov_text)
    if mentioned_zones:
        for zone in mentioned_zones:
            applicability_records.append({
                'provision_id': prov_id,
                'applies_to_zone': zone,
                'applies_to_all_zones': False,
                'applies_state_wide': False,
                'applies_to_lga': None,
                'excluded_zones': None,
                'applicability_source': 'text_mention',
                'confidence_score': 0.7,
                'notes': f'Zone {zone} mentioned in provision text'
            })
        return applicability_records

    # Case 4: Infer from document type
    doc_info = get_document_type_applicability(document_id)

    if doc_info['state_wide']:
        # SEPP - applies state-wide
        applicability_records.append({
            'provision_id': prov_id,
            'applies_to_zone': None,
            'applies_to_all_zones': True,
            'applies_state_wide': True,
            'applies_to_lga': None,
            'excluded_zones': None,
            'applicability_source': 'sepp_state_wide',
            'confidence_score': 0.8,
            'notes': 'SEPP provision - applies state-wide unless specific zones mentioned'
        })
    elif doc_info['lga']:
        # LEP/DCP - applies to all zones within LGA
        applicability_records.append({
            'provision_id': prov_id,
            'applies_to_zone': None,
            'applies_to_all_zones': True,
            'applies_state_wide': False,
            'applies_to_lga': doc_info['lga'],
            'excluded_zones': None,
            'applicability_source': 'lga_wide',
            'confidence_score': 0.6,
            'notes': f'General provision for {doc_info["lga"]} LGA'
        })
    else:
        # Unknown - context-dependent
        applicability_records.append({
            'provision_id': prov_id,
            'applies_to_zone': None,
            'applies_to_all_zones': False,
            'applies_state_wide': False,
            'applies_to_lga': None,
            'excluded_zones': None,
            'applicability_source': 'context_dependent',
            'confidence_score': 0.3,
            'notes': 'Applicability depends on development context'
        })

    return applicability_records


def process_provisions_batch(conn, batch_size=500):
    """
    Process all provisions and populate provision_applicability table
    """
    cur = conn.cursor()

    # Get total count
    cur.execute("SELECT COUNT(*) FROM regulatory_provisions")
    total_provisions = cur.fetchone()[0]

    print(f"Processing {total_provisions:,} provisions for zone applicability...")
    print()

    offset = 0
    processed = 0
    total_applicability_records = 0

    # Statistics
    stats = {
        'explicit_zone': 0,
        'text_all_zones': 0,
        'text_mention': 0,
        'sepp_state_wide': 0,
        'lga_wide': 0,
        'context_dependent': 0
    }

    while True:
        # Fetch batch
        cur.execute("""
            SELECT id, provision_text, zone, document_id
            FROM regulatory_provisions
            ORDER BY id
            LIMIT %s OFFSET %s
        """, (batch_size, offset))

        batch = cur.fetchall()
        if not batch:
            break

        batch_records = []

        for prov_id, prov_text, zone, doc_id in batch:
            provision = {
                'id': prov_id,
                'provision_text': prov_text,
                'zone': zone,
                'document_id': doc_id
            }

            applicability_records = determine_applicability(provision)

            for record in applicability_records:
                stats[record['applicability_source']] += 1
                batch_records.append((
                    record['provision_id'],
                    record['applies_to_zone'],
                    record['applies_to_all_zones'],
                    record['applies_to_lga'],
                    record['applies_state_wide'],
                    record['excluded_zones'],
                    record['applicability_source'],
                    record['confidence_score'],
                    record['notes']
                ))

        # Bulk insert
        if batch_records:
            insert_query = """
                INSERT INTO provision_applicability
                (provision_id, applies_to_zone, applies_to_all_zones, applies_to_lga,
                 applies_state_wide, excluded_zones, applicability_source,
                 confidence_score, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """
            cur.executemany(insert_query, batch_records)
            conn.commit()

            total_applicability_records += len(batch_records)

        processed += len(batch)
        offset += batch_size

        # Progress update
        if processed % 2500 == 0:
            pct = (processed / total_provisions) * 100
            print(f"  Processed {processed:,}/{total_provisions:,} ({pct:.1f}%) - " +
                  f"{total_applicability_records:,} applicability records created")

    cur.close()

    print(f"\nComplete!")
    print(f"  Total provisions processed: {processed:,}")
    print(f"  Total applicability records: {total_applicability_records:,}")
    print()
    print("Applicability sources:")
    for source, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        pct = (count / max(total_applicability_records, 1)) * 100
        print(f"  {source:20s}: {count:6,} ({pct:5.1f}%)")

    return processed, total_applicability_records, stats


def generate_statistics(conn):
    """Generate zone applicability statistics"""
    cur = conn.cursor()

    print("\n" + "=" * 80)
    print("ZONE APPLICABILITY STATISTICS")
    print("=" * 80)

    # Provisions now with zone applicability
    cur.execute("""
        SELECT COUNT(DISTINCT provision_id)
        FROM provision_applicability
    """)
    covered = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM regulatory_provisions")
    total = cur.fetchone()[0]

    print(f"\nProvisions with applicability defined: {covered:,} / {total:,} ({(covered/total)*100:.1f}%)")

    # By source
    cur.execute("""
        SELECT applicability_source, COUNT(*) as count
        FROM provision_applicability
        GROUP BY applicability_source
        ORDER BY count DESC
    """)
    print("\nBy applicability source:")
    for source, count in cur.fetchall():
        print(f"  {source:25s}: {count:,}")

    # State-wide provisions
    cur.execute("""
        SELECT COUNT(*)
        FROM provision_applicability
        WHERE applies_state_wide = TRUE
    """)
    state_wide = cur.fetchone()[0]
    print(f"\nState-wide provisions: {state_wide:,}")

    # LGA-specific provisions
    cur.execute("""
        SELECT applies_to_lga, COUNT(*) as count
        FROM provision_applicability
        WHERE applies_to_lga IS NOT NULL
        GROUP BY applies_to_lga
        ORDER BY count DESC
    """)
    print("\nLGA-specific provisions:")
    for lga, count in cur.fetchall():
        print(f"  {lga:20s}: {count:,}")

    # Zone-specific provisions
    cur.execute("""
        SELECT applies_to_zone, COUNT(*) as count
        FROM provision_applicability
        WHERE applies_to_zone IS NOT NULL
        GROUP BY applies_to_zone
        ORDER BY count DESC
        LIMIT 15
    """)
    print("\nTop zones with specific provisions:")
    for zone, count in cur.fetchall():
        print(f"  {zone:10s}: {count:,}")

    # Universal provisions
    cur.execute("""
        SELECT COUNT(*)
        FROM provision_applicability
        WHERE applies_to_all_zones = TRUE
    """)
    universal = cur.fetchone()[0]
    print(f"\nUniversal provisions (all zones): {universal:,}")

    cur.close()


if __name__ == "__main__":
    print("Phase 1: Zone Applicability Parsing")
    print("=" * 80)

    conn = get_connection()

    try:
        # Process all provisions
        processed, total_records, stats = process_provisions_batch(conn, batch_size=1000)

        # Generate statistics
        generate_statistics(conn)

        print("\n" + "=" * 80)
        print("Zone applicability parsing complete!")
        print("=" * 80)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()
