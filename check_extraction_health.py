#!/usr/bin/env python3
"""
Health check during extraction process
Monitors database state and alerts on anomalies
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from db_safety_wrapper import get_safe_connection

def health_check():
    conn = get_safe_connection()
    cursor = conn.cursor()

    print("="*60)
    print("EXTRACTION HEALTH CHECK")
    print("="*60)

    # Check 1: Total provision count
    cursor.execute("SELECT COUNT(*) FROM regulatory_provisions;")
    total = cursor.fetchone()[0]
    print(f"\n1. Total provisions: {total:,}")
    if total < 20000:
        print("   [WARNING] Provision count too low!")
        return False

    # Check 2: pdf_page coverage
    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE pdf_page IS NOT NULL) as with_page,
            COUNT(*) as total,
            ROUND(100.0 * COUNT(*) FILTER (WHERE pdf_page IS NOT NULL) / COUNT(*), 1) as pct
        FROM regulatory_provisions;
    """)
    with_page, total, pct = cursor.fetchone()
    print(f"2. PDF page coverage: {with_page:,}/{total:,} ({pct}%)")
    if pct < 20:
        print("   [WARNING] Coverage dropped below baseline!")
        return False

    # Check 3: Orphaned provisions
    cursor.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions rp
        LEFT JOIN documents d ON rp.document_id = d.id
        WHERE d.id IS NULL;
    """)
    orphaned = cursor.fetchone()[0]
    print(f"3. Orphaned provisions: {orphaned:,}")
    if orphaned > 100:
        print("   [WARNING] Too many orphaned provisions!")
        return False

    # Check 4: Image provisions
    cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE ref_number LIKE 'img_%';")
    images = cursor.fetchone()[0]
    print(f"4. Image provisions: {images:,}")

    # Check 5: Database size
    cursor.execute("""
        SELECT pg_size_pretty(pg_database_size('nsw_planning'));
    """)
    size = cursor.fetchone()[0]
    print(f"5. Database size: {size}")

    print("\n" + "="*60)
    print("[SUCCESS] ALL CHECKS PASSED")
    print("="*60)

    cursor.close()
    conn.close()
    return True

if __name__ == "__main__":
    success = health_check()
    sys.exit(0 if success else 1)
