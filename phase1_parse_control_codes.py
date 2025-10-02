"""
Phase 1: Parse Control Codes from Provision ref_number
Objective: Split multi-code provisions (C17, C18, C19) into individual searchable records
"""

import psycopg2
import re
from typing import List, Dict

def get_connection():
    return psycopg2.connect(
        host='localhost',
        database='nsw_planning',
        user='postgres',
        password='postgres',
        port=5432
    )


def parse_control_codes(ref_number: str) -> List[str]:
    """
    Parse comma-separated or range-based control codes

    Examples:
      "C17, C18, C19, C20" → ['C17', 'C18', 'C19', 'C20']
      "C17-C20" → ['C17', 'C18', 'C19', 'C20']
      "3.2.1" → ['3.2.1']
    """
    if not ref_number:
        return []

    codes = []

    # Check for comma-separated codes
    if ',' in ref_number:
        parts = [p.strip() for p in ref_number.split(',')]
        codes.extend(parts)

    # Check for range notation (C17-C20)
    elif '-' in ref_number and not ref_number.replace('-', '').replace('.', '').isdigit():
        # Extract start and end
        match = re.match(r'([A-Z]+)(\d+)-([A-Z]+)(\d+)', ref_number)
        if match:
            prefix1, start, prefix2, end = match.groups()
            if prefix1 == prefix2:
                start_num = int(start)
                end_num = int(end)
                for i in range(start_num, end_num + 1):
                    codes.append(f'{prefix1}{i}')
        else:
            # Not a valid range, treat as single code
            codes.append(ref_number)

    else:
        # Single code
        codes.append(ref_number)

    return [c for c in codes if c]  # Remove empty strings


def consolidate_code_range(codes: List[str]) -> str:
    """
    Consolidate sequential codes into range format for display

    Examples:
      ['C17', 'C18', 'C19', 'C20'] → 'C17-C20'
      ['C17', 'C19'] → 'C17, C19'
      ['3.2.1'] → '3.2.1'
    """
    if len(codes) <= 1:
        return codes[0] if codes else ''

    # Try to find sequential pattern
    # Extract prefix and numbers
    prefix = codes[0].rstrip('0123456789')
    numbers = []

    for code in codes:
        if not code.startswith(prefix):
            # Mixed prefixes, return comma-separated
            return ', '.join(codes)

        try:
            num = int(code[len(prefix):])
            numbers.append(num)
        except ValueError:
            # Non-numeric suffix, return comma-separated
            return ', '.join(codes)

    # Check if sequential
    numbers.sort()
    is_sequential = all(numbers[i+1] - numbers[i] == 1 for i in range(len(numbers)-1))

    if is_sequential and len(numbers) >= 3:
        # Use range notation
        return f'{prefix}{numbers[0]}-{prefix}{numbers[-1]}'
    else:
        # Use comma-separated
        return ', '.join(codes)


def infer_control_type(ref_number: str, provision_text: str) -> str:
    """
    Infer control type from reference number and provision text

    Types: setback, height, fsr, parking, heritage, environmental, general
    """
    if not provision_text:
        return 'general'

    text_lower = provision_text.lower()

    # Check for keywords
    if any(word in text_lower for word in ['setback', 'boundary', 'siting']):
        return 'setback'
    elif any(word in text_lower for word in ['height', 'storey', 'floor level']):
        return 'height'
    elif any(word in text_lower for word in ['fsr', 'floor space ratio', 'floor area']):
        return 'fsr'
    elif any(word in text_lower for word in ['parking', 'vehicle', 'car space']):
        return 'parking'
    elif any(word in text_lower for word in ['heritage', 'conservation', 'historic']):
        return 'heritage'
    elif any(word in text_lower for word in ['environment', 'biodiversity', 'vegetation', 'tree']):
        return 'environmental'
    elif any(word in text_lower for word in ['landscap', 'garden', 'open space']):
        return 'landscaping'
    else:
        return 'general'


def process_provisions_batch(conn, batch_size=1000):
    """
    Process all provisions and populate control_codes table
    """
    cur = conn.cursor()

    # Get total count
    cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE ref_number IS NOT NULL")
    total_provisions = cur.fetchone()[0]

    print(f"Processing {total_provisions:,} provisions for control codes...")
    print()

    offset = 0
    processed = 0
    total_codes = 0
    multi_code_count = 0

    # Statistics by control type
    control_type_stats = {}

    while True:
        # Fetch batch
        cur.execute("""
            SELECT id, ref_number, provision_text
            FROM regulatory_provisions
            WHERE ref_number IS NOT NULL
            ORDER BY id
            LIMIT %s OFFSET %s
        """, (batch_size, offset))

        batch = cur.fetchall()
        if not batch:
            break

        batch_records = []

        for prov_id, ref_number, prov_text in batch:
            # Parse codes
            codes = parse_control_codes(ref_number)

            if len(codes) > 1:
                multi_code_count += 1
                code_group = consolidate_code_range(codes)
            else:
                code_group = ref_number

            # Infer control type
            control_type = infer_control_type(ref_number, prov_text)
            control_type_stats[control_type] = control_type_stats.get(control_type, 0) + len(codes)

            # Create records for each code
            for seq, code in enumerate(codes, start=1):
                batch_records.append((
                    code,
                    prov_id,
                    code_group,
                    control_type,
                    seq,
                    seq == 1,  # is_range_start
                    seq == len(codes)  # is_range_end
                ))

        # Bulk insert
        if batch_records:
            insert_query = """
                INSERT INTO control_codes
                (code, provision_id, code_group, control_type, sequence_number,
                 is_range_start, is_range_end)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (code, provision_id) DO NOTHING
            """
            cur.executemany(insert_query, batch_records)
            conn.commit()

            total_codes += len(batch_records)

        processed += len(batch)
        offset += batch_size

        # Progress update
        if processed % 5000 == 0:
            pct = (processed / total_provisions) * 100
            print(f"  Processed {processed:,}/{total_provisions:,} ({pct:.1f}%) - " +
                  f"{total_codes:,} control codes created")

    cur.close()

    print(f"\nComplete!")
    print(f"  Total provisions processed: {processed:,}")
    print(f"  Multi-code provisions: {multi_code_count:,}")
    print(f"  Total control code records: {total_codes:,}")
    print()
    print("Control types:")
    for ctrl_type, count in sorted(control_type_stats.items(), key=lambda x: x[1], reverse=True):
        pct = (count / max(total_codes, 1)) * 100
        print(f"  {ctrl_type:20s}: {count:6,} ({pct:5.1f}%)")

    return processed, total_codes, multi_code_count


def generate_statistics(conn):
    """Generate control code statistics"""
    cur = conn.cursor()

    print("\n" + "=" * 80)
    print("CONTROL CODE STATISTICS")
    print("=" * 80)

    # Total codes
    cur.execute("SELECT COUNT(*) FROM control_codes")
    total = cur.fetchone()[0]
    print(f"\nTotal control code records: {total:,}")

    # Unique codes
    cur.execute("SELECT COUNT(DISTINCT code) FROM control_codes")
    unique = cur.fetchone()[0]
    print(f"Unique codes: {unique:,}")

    # By control type
    cur.execute("""
        SELECT control_type, COUNT(*) as count
        FROM control_codes
        GROUP BY control_type
        ORDER BY count DESC
    """)
    print("\nBy control type:")
    for ctrl_type, count in cur.fetchall():
        print(f"  {ctrl_type:20s}: {count:,}")

    # Most common codes
    cur.execute("""
        SELECT code, COUNT(*) as provision_count
        FROM control_codes
        GROUP BY code
        ORDER BY provision_count DESC
        LIMIT 15
    """)
    print("\nMost common control codes:")
    for code, count in cur.fetchall():
        print(f"  {code:15s}: {count:,} provisions")

    # Example consolidated codes
    cur.execute("""
        SELECT code_group, COUNT(DISTINCT provision_id) as prov_count, control_type
        FROM control_codes
        WHERE code_group LIKE '%-%'
        GROUP BY code_group, control_type
        ORDER BY prov_count DESC
        LIMIT 10
    """)
    print("\nConsolidated code ranges (examples):")
    for code_group, prov_count, ctrl_type in cur.fetchall():
        print(f"  {code_group:20s}: {prov_count:3,} provisions ({ctrl_type})")

    cur.close()


if __name__ == "__main__":
    print("Phase 1: Control Code Parsing")
    print("=" * 80)

    conn = get_connection()

    try:
        # Process all provisions
        processed, total_codes, multi_code_count = process_provisions_batch(conn, batch_size=2000)

        # Generate statistics
        generate_statistics(conn)

        print("\n" + "=" * 80)
        print("Control code parsing complete!")
        print("=" * 80)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()
