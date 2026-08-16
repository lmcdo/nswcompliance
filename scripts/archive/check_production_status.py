"""Check production database status to determine recovery path."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_production_status():
    """Check if production database has correct data."""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()

    # Check provision counts and actionable status
    query = """
    SELECT
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE v2_is_actionable = true) as actionable,
        COUNT(*) FILTER (WHERE v2_is_actionable = false) as non_actionable,
        COUNT(*) FILTER (WHERE v2_is_actionable IS NULL) as null_actionable
    FROM regulatory_provisions;
    """

    cur.execute(query)
    result = cur.fetchone()

    total, actionable, non_actionable, null_actionable = result

    print("\n" + "="*70)
    print("PRODUCTION DATABASE STATUS CHECK")
    print("="*70)
    print(f"\nTotal provisions: {total:,}")
    print(f"  [OK] Actionable (TRUE):     {actionable:,}")
    print(f"  [X]  Non-actionable (FALSE): {non_actionable:,}")
    print(f"  [?]  NULL values:            {null_actionable:,}")

    # Determine if production is intact
    print("\n" + "="*70)
    print("RECOVERY PATH DETERMINATION")
    print("="*70)

    if actionable >= 11000:  # Should be ~11,835
        print("\n[SUCCESS] PRODUCTION DATABASE IS INTACT!")
        print(f"   Found {actionable:,} actionable provisions (expected ~11,835)")
        print("\n   RECOMMENDED ACTION: Direct restore from production")
        print("   Next step: Run dump_production_to_backup.py")
        return "INTACT"

    elif null_actionable == total:
        print("\n[ERROR] PRODUCTION DATABASE IS CORRUPTED!")
        print("   All provisions have NULL actionable status")
        print("\n   RECOMMENDED ACTION: Rebuild from Nov 24 backup")
        print("   Next step: restore_from_backup.py with Nov 24 file")
        return "CORRUPTED_NULL"

    elif actionable == 0:
        print("\n[ERROR] PRODUCTION DATABASE IS CORRUPTED!")
        print("   Zero actionable provisions found")
        print("\n   RECOMMENDED ACTION: Rebuild from Nov 24 backup")
        print("   Next step: restore_from_backup.py with Nov 24 file")
        return "CORRUPTED_ZERO"

    else:
        print("\n[WARNING] PRODUCTION DATABASE IS PARTIALLY DAMAGED")
        print(f"   Only {actionable:,} actionable provisions (expected ~11,835)")
        print("\n   RECOMMENDED ACTION: Investigate further or rebuild")
        print("   Next step: Review data or restore from Nov 24 backup")
        return "PARTIAL"

    cur.close()
    conn.close()

if __name__ == "__main__":
    try:
        status = check_production_status()
        print("\n" + "="*70)
        print(f"Status Code: {status}")
        print("="*70 + "\n")
    except Exception as e:
        print(f"\n[ERROR]: {e}")
        print("\nCould not connect to production database.")
        print("Check .env file DATABASE_URL configuration.")
