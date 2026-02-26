"""
Fix A: Mark Statutory Information provisions as non-actionable for Marrickville.
These are administrative/intro provisions from the Statutory Information document
that are incorrectly tagged as v2_is_actionable = true.

Safe to run: confirmed 6 rows, all from Statutory_Information document.
"""
import psycopg2
import os

DATABASE_URL = os.getenv('DATABASE_URL')

def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Preview the rows
    cur.execute("""
        SELECT id, document_id, LEFT(provision_text, 150) as text_preview
        FROM regulatory_provisions
        WHERE former_council = 'marrickville'
          AND document_id ILIKE '%Statutory_Information%'
          AND v2_is_actionable = true
        ORDER BY id
    """)
    rows = cur.fetchall()
    print(f"Fix A preview: {len(rows)} rows to mark v2_is_actionable = false")
    print()
    for r in rows:
        print(f"  id={r[0]}")
        print(f"  doc={r[1]}")
        print(f"  text: {r[2]!r}")
        print()

    if len(rows) == 0:
        print("Nothing to fix.")
        conn.close()
        return

    # Also sample some OCR artifact provisions to understand their pattern
    print("=" * 60)
    print("OCR artifact provisions sample (for analysis, not fixing now):")
    cur.execute("""
        SELECT id, document_id, LEFT(provision_text, 300) as text_preview
        FROM regulatory_provisions
        WHERE former_council = 'marrickville'
          AND v2_is_actionable = true
          AND provision_text ~ '^PART [0-9A-Z]'
        ORDER BY id
        LIMIT 10
    """)
    ocr_rows = cur.fetchall()
    print(f"OCR artifacts sample: {len(ocr_rows)} of total")
    for r in ocr_rows:
        print(f"\n  id={r[0]}")
        print(f"  doc={r[1]}")
        print(f"  text first 300 chars: {r[2]!r}")

    print()
    confirm = input(f"\nApply Fix A ({len(rows)} rows)? [yes/no]: ").strip().lower()
    if confirm != 'yes':
        print("Aborted.")
        conn.close()
        return

    # Apply Fix A
    cur.execute("""
        UPDATE regulatory_provisions
        SET v2_is_actionable = false
        WHERE former_council = 'marrickville'
          AND document_id ILIKE '%Statutory_Information%'
          AND v2_is_actionable = true
    """)
    updated = cur.rowcount
    conn.commit()
    print(f"Fixed {updated} rows.")
    conn.close()

if __name__ == '__main__':
    main()
