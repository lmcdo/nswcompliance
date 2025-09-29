import sys
sys.stdout.reconfigure(encoding='utf-8')

from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Check regulatory_provisions table structure
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'regulatory_provisions'
            ORDER BY ordinal_position
        """)
        columns = [c[0] for c in cur.fetchall()]
        print(f"Columns in regulatory_provisions: {columns}\n")

        # Check total provisions
        cur.execute('SELECT COUNT(*) FROM regulatory_provisions')
        total = cur.fetchone()[0]

        # Check provisions with full text - try different column names
        text_columns = ['full_text', 'full_provision_text', 'provision_text', 'text']
        text_column = None
        for col in text_columns:
            if col in columns:
                text_column = col
                break

        if text_column:
            cur.execute(f"SELECT COUNT(*) FROM regulatory_provisions WHERE {text_column} IS NOT NULL AND {text_column} != ''")
            with_text = cur.fetchone()[0]
            print(f'Overall coverage: {with_text}/{total} ({with_text*100/total:.1f}%)')
        else:
            print(f"Could not find text column. Available columns: {columns}")

        # Check Exempt SEPP specifically if source_document column exists
        if 'source_document' in columns:
            cur.execute("""
                SELECT COUNT(*)
                FROM regulatory_provisions
                WHERE source_document LIKE '%Exempt%'
            """)
            exempt_total = cur.fetchone()[0]

            if text_column:
                cur.execute(f"""
                    SELECT COUNT(*)
                    FROM regulatory_provisions
                    WHERE source_document LIKE '%Exempt%'
                    AND {text_column} IS NOT NULL AND {text_column} != ''
                """)
                exempt_with_text = cur.fetchone()[0]
                print(f'Exempt SEPP coverage: {exempt_with_text}/{exempt_total} ({exempt_with_text*100/exempt_total:.1f}%)')