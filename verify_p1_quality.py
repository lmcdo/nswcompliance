#!/usr/bin/env python3
"""
Verify PRP-P1 Data Quality
Check if 958 permissibility_analysis records match P1 specifications
"""

from db_config import get_connection
import json

def verify_p1_data_quality():
    conn = get_connection()
    cur = conn.cursor()

    print("=" * 70)
    print("PRP-P1 DATA QUALITY VERIFICATION")
    print("=" * 70)

    # 1. Count and sample records
    cur.execute("SELECT COUNT(*) FROM permissibility_analysis")
    total_count = cur.fetchone()[0]
    print(f"\n[OK] Total records: {total_count} (target: 500+)")
    print(f"  Status: {'PASS' if total_count >= 500 else 'FAIL'}")

    # 2. Check required fields populated
    print("\n--- Field Population Check ---")
    required_fields = [
        'provision_id', 'zone', 'pattern_type',
        'extracted_text', 'development_types', 'permission_status'
    ]

    for field in required_fields:
        cur.execute(f"SELECT COUNT(*) FROM permissibility_analysis WHERE {field} IS NOT NULL AND {field} != ''")
        populated = cur.fetchone()[0]
        percentage = (populated / total_count * 100) if total_count > 0 else 0
        status = "PASS" if percentage >= 90 else "FAIL"
        print(f"  {field:20s}: {populated:4d}/{total_count:4d} ({percentage:5.1f}%) [{status}]")

    # 3. Sample records for manual inspection
    print("\n--- Sample Records (First 5) ---")
    cur.execute("""
        SELECT id, zone, pattern_type, extracted_text, development_types, permission_status
        FROM permissibility_analysis
        LIMIT 5
    """)

    for i, row in enumerate(cur.fetchall(), 1):
        print(f"\nRecord {i}:")
        print(f"  ID: {row[0]}")
        print(f"  Zone: {row[1]}")
        print(f"  Pattern Type: {row[2]}")
        print(f"  Extracted Text: {row[3][:100]}..." if row[3] and len(row[3]) > 100 else f"  Extracted Text: {row[3]}")
        print(f"  Development Types: {row[4]}")
        print(f"  Permission Status: {row[5]}")

    # 4. Check pattern type distribution
    print("\n--- Pattern Type Distribution ---")
    cur.execute("""
        SELECT pattern_type, COUNT(*) as count
        FROM permissibility_analysis
        WHERE pattern_type IS NOT NULL
        GROUP BY pattern_type
        ORDER BY count DESC
    """)

    pattern_types = cur.fetchall()
    print(f"  Unique pattern types: {len(pattern_types)}")
    for pt, count in pattern_types:
        print(f"    {pt:30s}: {count:4d} records")

    # 5. Check zone coverage
    print("\n--- Zone Coverage ---")
    cur.execute("""
        SELECT zone, COUNT(*) as count
        FROM permissibility_analysis
        WHERE zone IS NOT NULL
        GROUP BY zone
        ORDER BY count DESC
    """)

    zones = cur.fetchall()
    print(f"  Unique zones: {len(zones)} (target: 15+)")
    print(f"  Status: {'PASS' if len(zones) >= 15 else 'FAIL'}")
    for zone, count in zones[:10]:  # Show top 10
        print(f"    {zone:10s}: {count:4d} records")

    # 6. Check permission status distribution
    print("\n--- Permission Status Distribution ---")
    cur.execute("""
        SELECT permission_status, COUNT(*) as count
        FROM permissibility_analysis
        WHERE permission_status IS NOT NULL
        GROUP BY permission_status
        ORDER BY count DESC
    """)

    statuses = cur.fetchall()
    expected_statuses = ['permitted', 'prohibited', 'consent']
    found_statuses = [s[0] for s in statuses if s[0]]

    print(f"  Expected statuses: {expected_statuses}")
    print(f"  Found statuses: {found_statuses}")
    print(f"  Status: {'PASS' if all(s in found_statuses for s in expected_statuses) else 'FAIL'}")

    for status, count in statuses:
        print(f"    {status:15s}: {count:4d} records")

    # 7. Check development_types JSON validity
    print("\n--- Development Types JSON Validation ---")
    cur.execute("SELECT development_types FROM permissibility_analysis WHERE development_types IS NOT NULL LIMIT 10")

    valid_json = 0
    invalid_json = 0

    for row in cur.fetchall():
        try:
            if row[0]:
                json.loads(row[0])
                valid_json += 1
        except:
            invalid_json += 1

    print(f"  Valid JSON: {valid_json}/10 samples")
    print(f"  Invalid JSON: {invalid_json}/10 samples")
    print(f"  Status: {'PASS' if invalid_json == 0 else 'FAIL'}")

    # 8. Overall Assessment
    print("\n" + "=" * 70)
    print("OVERALL ASSESSMENT")
    print("=" * 70)

    issues = []
    if total_count < 500:
        issues.append(f"Record count below target ({total_count} < 500)")
    if len(zones) < 15:
        issues.append(f"Zone coverage below target ({len(zones)} < 15)")
    if not all(s in found_statuses for s in expected_statuses):
        issues.append("Missing expected permission statuses")
    if invalid_json > 0:
        issues.append("Invalid JSON in development_types field")

    if not issues:
        print("[PASS] PRP-P1 DATA QUALITY: PASS")
        print("  All checks passed - data meets specifications")
        print("\nRECOMMENDATION: Proceed with PRP-P2 validation")
    else:
        print("[FAIL] PRP-P1 DATA QUALITY: FAIL")
        print("\nIssues found:")
        for issue in issues:
            print(f"  - {issue}")
        print("\nRECOMMENDATION: Re-run PRP-P1 extraction")

    conn.close()

if __name__ == "__main__":
    verify_p1_data_quality()