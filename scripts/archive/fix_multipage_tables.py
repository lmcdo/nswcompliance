#!/usr/bin/env python3
"""
Fix multi-page tables that were split by Camelot

Problem: Large parking rate tables span 2-3 pages, but Camelot extracted each page separately
Solution: Detect and merge table fragments that span consecutive pages
"""
import psycopg2
import re

DB_CONFIG = {
    'dbname': 'nsw_planning',
    'user': 'postgres',
    'password': 'Sturt1802!',
    'host': 'localhost'
}

# Known multi-page table fragments (from analysis)
MULTI_PAGE_TABLES = [
    {
        'name': 'Ashfield Parking Rates - Pages 64-65',
        'fragments': [58309, 58310],  # Market table continues across pages
        'primary_id': 58309,  # Keep this provision, merge others into it
    },
    {
        'name': 'Ashfield Parking Rates - Pages 66-67',
        'fragments': [58312, 58314],  # Place of Worship table continues
        'primary_id': 58312,
    }
]


def merge_table_html(fragments: list) -> str:
    """Merge HTML table fragments into single table"""

    # Remove opening/closing table tags and merge tbody content
    merged_rows = []

    for i, html in enumerate(fragments):
        # Extract rows from this fragment
        # Remove table/tbody tags
        html = html.replace('<table>', '').replace('</table>', '')
        html = html.replace('<tbody>', '').replace('</tbody>', '')
        html = html.replace('<thead>', '').replace('</thead>', '')

        # Keep header from first fragment only
        if i == 0:
            # Keep everything
            merged_rows.append(html)
        else:
            # Skip header row if present, merge data rows only
            rows = re.findall(r'<tr>.*?</tr>', html, re.DOTALL)

            for row in rows:
                # Skip if looks like header (contains <th> or ALL CAPS)
                if '<th>' in row:
                    continue
                if all(cell.isupper() for cell in re.findall(r'<td>(.*?)</td>', row)):
                    continue

                merged_rows.append(row)

    # Reconstruct complete table
    merged_html = '<table><tbody>\n' + '\n'.join(merged_rows) + '\n</tbody></table>'

    return merged_html


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("=" * 70)
    print("Fixing Multi-Page Table Splits")
    print("=" * 70)
    print()

    for table_group in MULTI_PAGE_TABLES:
        print(f"\n[MERGING] {table_group['name']}")
        print(f"  Primary ID: {table_group['primary_id']}")
        print(f"  Fragments: {table_group['fragments']}")

        # Fetch all fragments
        fragment_htmls = []
        for frag_id in table_group['fragments']:
            cur.execute(
                "SELECT provision_text FROM regulatory_provisions WHERE id = %s",
                (frag_id,)
            )
            result = cur.fetchone()
            if result:
                fragment_htmls.append(result[0])

        if len(fragment_htmls) != len(table_group['fragments']):
            print(f"  [ERROR] Could not fetch all fragments")
            continue

        # Merge fragments
        merged_html = merge_table_html(fragment_htmls)

        print(f"  [OK] Merged {len(fragment_htmls)} fragments")
        print(f"  Original lengths: {[len(h) for h in fragment_htmls]}")
        print(f"  Merged length: {len(merged_html)}")

        # Update primary provision with merged table
        cur.execute(
            """
            UPDATE regulatory_provisions
            SET provision_text = %s
            WHERE id = %s
            """,
            (merged_html, table_group['primary_id'])
        )

        print(f"  [OK] Updated provision {table_group['primary_id']}")

        # Delete fragment provisions (they're now merged)
        for frag_id in table_group['fragments']:
            if frag_id != table_group['primary_id']:
                cur.execute(
                    """
                    DELETE FROM regulatory_provisions
                    WHERE id = %s
                    """,
                    (frag_id,)
                )
                print(f"  [OK] Deleted fragment provision {frag_id}")

    conn.commit()
    cur.close()
    conn.close()

    print("\n" + "=" * 70)
    print("[DONE] Multi-page table merging complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
