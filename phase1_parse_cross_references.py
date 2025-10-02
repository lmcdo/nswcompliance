"""
Phase 1: Parse Cross-References from Provision Text
Objective: Extract and index all cross-references for fast resolution
"""

import psycopg2
import re
from typing import List, Dict, Tuple
from datetime import datetime

# Database connection
def get_connection():
    return psycopg2.connect(
        host='localhost',
        database='nsw_planning',
        user='postgres',
        password='postgres',
        port=5432
    )


def extract_cross_references(provision_text: str) -> List[Dict]:
    """
    Extract cross-references from provision text using regex patterns

    Returns list of dicts: {
        'type': 'section'|'clause'|'figure'|'part'|'chapter'|'table',
        'number': extracted number,
        'text': original text snippet,
        'is_mandatory': bool
    }
    """
    if not provision_text:
        return []

    references = []

    # Pattern 1: Section references (Section 8.3, Section 4.1.2)
    section_pattern = r'([Ss]ection\s+([\d\.]+[a-z]?))'
    for match in re.finditer(section_pattern, provision_text):
        full_text, number = match.groups()
        references.append({
            'type': 'section',
            'number': number,
            'text': full_text,
            'is_mandatory': 'refer to' in provision_text[max(0, match.start()-50):match.end()].lower()
                          or 'see' in provision_text[max(0, match.start()-20):match.end()].lower(),
            'context': provision_text[max(0, match.start()-100):min(len(provision_text), match.end()+100)]
        })

    # Pattern 2: Clause references (Clause 4.3, Clause 5.10)
    clause_pattern = r'([Cc]lause\s+([\d\.]+[a-z]?))'
    for match in re.finditer(clause_pattern, provision_text):
        full_text, number = match.groups()
        references.append({
            'type': 'clause',
            'number': number,
            'text': full_text,
            'is_mandatory': 'must' in provision_text[max(0, match.start()-30):match.end()].lower()
                          or 'required' in provision_text[max(0, match.start()-30):match.end()].lower(),
            'context': provision_text[max(0, match.start()-100):min(len(provision_text), match.end()+100)]
        })

    # Pattern 3: Figure references (Figure 11.1c, Figures 25.6)
    figure_pattern = r'([Ff]igure[s]?\s+([\d\.]+[a-z]?))'
    for match in re.finditer(figure_pattern, provision_text):
        full_text, number = match.groups()
        references.append({
            'type': 'figure',
            'number': number,
            'text': full_text,
            'is_mandatory': 'conform' in provision_text[max(0, match.start()-50):match.end()].lower()
                          or 'accordance' in provision_text[max(0, match.start()-50):match.end()].lower(),
            'context': provision_text[max(0, match.start()-100):min(len(provision_text), match.end()+100)]
        })

    # Pattern 4: Diagram references (Diagram 3.2)
    diagram_pattern = r'([Dd]iagram[s]?\s+([\d\.]+[a-z]?))'
    for match in re.finditer(diagram_pattern, provision_text):
        full_text, number = match.groups()
        references.append({
            'type': 'diagram',
            'number': number,
            'text': full_text,
            'is_mandatory': 'conform' in provision_text[max(0, match.start()-50):match.end()].lower(),
            'context': provision_text[max(0, match.start()-100):min(len(provision_text), match.end()+100)]
        })

    # Pattern 5: Table references (Table 4.1)
    table_pattern = r'([Tt]able[s]?\s+([\d\.]+))'
    for match in re.finditer(table_pattern, provision_text):
        full_text, number = match.groups()
        references.append({
            'type': 'table',
            'number': number,
            'text': full_text,
            'is_mandatory': False,
            'context': provision_text[max(0, match.start()-100):min(len(provision_text), match.end()+100)]
        })

    # Pattern 6: Part references (Part 8, Part E)
    part_pattern = r'([Pp]art\s+([A-Z\d]+))'
    for match in re.finditer(part_pattern, provision_text):
        full_text, number = match.groups()
        references.append({
            'type': 'part',
            'number': number,
            'text': full_text,
            'is_mandatory': 'refer to' in provision_text[max(0, match.start()-30):match.end()].lower(),
            'context': provision_text[max(0, match.start()-100):min(len(provision_text), match.end()+100)]
        })

    # Pattern 7: Chapter references (Chapter F, Chapter 11)
    chapter_pattern = r'([Cc]hapter\s+([A-Z\d]+))'
    for match in re.finditer(chapter_pattern, provision_text):
        full_text, number = match.groups()
        references.append({
            'type': 'chapter',
            'number': number,
            'text': full_text,
            'is_mandatory': False,
            'context': provision_text[max(0, match.start()-100):min(len(provision_text), match.end()+100)]
        })

    return references


def resolve_cross_reference(conn, source_provision_id: int, ref_type: str, ref_number: str) -> Tuple[int, str, float]:
    """
    Attempt to resolve cross-reference to target provision

    Returns: (target_provision_id, resolution_status, confidence_score)
    """
    cur = conn.cursor()

    # Get source provision document
    cur.execute("""
        SELECT document_id FROM regulatory_provisions
        WHERE id = %s
    """, (source_provision_id,))
    result = cur.fetchone()
    if not result:
        return None, 'unresolved', 0.0

    source_doc = result[0]

    # Try exact match in same document
    cur.execute("""
        SELECT id FROM regulatory_provisions
        WHERE document_id = %s
        AND ref_number = %s
        LIMIT 1
    """, (source_doc, ref_number))

    exact_match = cur.fetchone()
    if exact_match:
        cur.close()
        return exact_match[0], 'resolved', 1.0

    # Try partial match (e.g., '8.3' matches '8.3.1', '8.3.2')
    cur.execute("""
        SELECT id FROM regulatory_provisions
        WHERE document_id = %s
        AND ref_number LIKE %s
        ORDER BY ref_number
        LIMIT 5
    """, (source_doc, f'{ref_number}%'))

    partial_matches = cur.fetchall()
    cur.close()

    if len(partial_matches) == 1:
        return partial_matches[0][0], 'resolved', 0.8
    elif len(partial_matches) > 1:
        # Ambiguous - multiple possible targets
        return partial_matches[0][0], 'ambiguous', 0.5
    else:
        return None, 'unresolved', 0.0


def process_provisions_batch(conn, batch_size=100, resume_from_id=0):
    """
    Process provisions in batches to extract and store cross-references
    """
    cur = conn.cursor()

    # Get total count
    cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE id > %s", (resume_from_id,))
    total_provisions = cur.fetchone()[0]

    print(f"Processing {total_provisions:,} provisions starting from ID {resume_from_id}...")

    offset = 0
    processed = 0
    total_references = 0
    resolved_count = 0

    while True:
        # Fetch batch
        cur.execute("""
            SELECT id, provision_text, document_id
            FROM regulatory_provisions
            WHERE id > %s
            AND provision_text IS NOT NULL
            ORDER BY id
            LIMIT %s OFFSET %s
        """, (resume_from_id, batch_size, offset))

        batch = cur.fetchall()
        if not batch:
            break

        batch_references = []

        for prov_id, prov_text, doc_id in batch:
            # Extract references
            refs = extract_cross_references(prov_text)

            for ref in refs:
                # Attempt resolution for section/clause references
                target_id = None
                status = 'unresolved'
                confidence = 0.0

                if ref['type'] in ['section', 'clause']:
                    target_id, status, confidence = resolve_cross_reference(
                        conn, prov_id, ref['type'], ref['number']
                    )
                    if status == 'resolved':
                        resolved_count += 1

                batch_references.append((
                    prov_id,
                    ref['type'],
                    ref['number'],
                    ref['text'],
                    target_id,
                    status,
                    confidence,
                    ref['is_mandatory'],
                    ref['context']
                ))

        # Bulk insert
        if batch_references:
            insert_query = """
                INSERT INTO cross_reference_index
                (source_provision_id, reference_type, reference_number, reference_text,
                 target_provision_id, resolution_status, resolution_confidence,
                 is_mandatory, context_snippet)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """
            cur.executemany(insert_query, batch_references)
            conn.commit()

            total_references += len(batch_references)

        processed += len(batch)
        offset += batch_size

        # Progress update every 1000 provisions
        if processed % 1000 == 0:
            pct = (processed / total_provisions) * 100
            print(f"  Processed {processed:,}/{total_provisions:,} ({pct:.1f}%) - " +
                  f"{total_references:,} references found, {resolved_count:,} resolved")

    cur.close()

    print(f"\nComplete!")
    print(f"  Total provisions processed: {processed:,}")
    print(f"  Total cross-references extracted: {total_references:,}")
    print(f"  Resolved references: {resolved_count:,}")
    print(f"  Resolution rate: {(resolved_count/max(total_references,1))*100:.1f}%")

    return processed, total_references, resolved_count


def generate_statistics(conn):
    """Generate summary statistics"""
    cur = conn.cursor()

    print("\n" + "=" * 80)
    print("CROSS-REFERENCE STATISTICS")
    print("=" * 80)

    # Total references by type
    cur.execute("""
        SELECT reference_type, COUNT(*) as count
        FROM cross_reference_index
        GROUP BY reference_type
        ORDER BY count DESC
    """)
    print("\nReferences by type:")
    for ref_type, count in cur.fetchall():
        print(f"  {ref_type:15s}: {count:,}")

    # Resolution status
    cur.execute("""
        SELECT resolution_status, COUNT(*) as count
        FROM cross_reference_index
        GROUP BY resolution_status
        ORDER BY count DESC
    """)
    print("\nResolution status:")
    for status, count in cur.fetchall():
        print(f"  {status:15s}: {count:,}")

    # Mandatory vs optional
    cur.execute("""
        SELECT is_mandatory, COUNT(*) as count
        FROM cross_reference_index
        GROUP BY is_mandatory
    """)
    print("\nMandatory references:")
    for is_mand, count in cur.fetchall():
        mand_label = "Mandatory" if is_mand else "Optional"
        print(f"  {mand_label:15s}: {count:,}")

    # Top referenced provisions
    cur.execute("""
        SELECT
            target_provision_id,
            rp.ref_number,
            rp.document_id,
            COUNT(*) as reference_count
        FROM cross_reference_index xr
        JOIN regulatory_provisions rp ON xr.target_provision_id = rp.id
        WHERE target_provision_id IS NOT NULL
        GROUP BY target_provision_id, rp.ref_number, rp.document_id
        ORDER BY reference_count DESC
        LIMIT 10
    """)
    print("\nMost referenced provisions:")
    for target_id, ref_num, doc_id, count in cur.fetchall():
        doc_short = doc_id[:50] + "..." if len(doc_id) > 50 else doc_id
        print(f"  {ref_num:10s} ({doc_short}): {count} references")

    cur.close()


if __name__ == "__main__":
    print("Phase 1: Cross-Reference Parsing")
    print("=" * 80)

    conn = get_connection()

    try:
        # Process all provisions
        processed, total_refs, resolved = process_provisions_batch(conn, batch_size=500)

        # Generate statistics
        generate_statistics(conn)

        print("\n" + "=" * 80)
        print("Cross-reference parsing complete!")
        print("=" * 80)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()
