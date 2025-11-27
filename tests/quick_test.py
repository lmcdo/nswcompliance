"""Check: Heritage vs Non-Heritage Demolition provisions"""
import psycopg2

conn = psycopg2.connect('postgresql://postgres:Onlyme123!@127.0.0.1:5432/nsw_planning')
cur = conn.cursor()

print("=" * 70)
print("HERITAGE vs NON-HERITAGE DEMOLITION")
print("=" * 70)

councils = ['Marrickville', 'Ashfield', 'Leichhardt']

for council in councils:
    print(f"\n### {council.upper()} ###")

    # Demolition provisions IN heritage context
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE document_id ILIKE %s
        AND provision_text ILIKE '%%demolition%%'
        AND (
            v2_topic ILIKE '%%heritage%%'
            OR document_id ILIKE '%%heritage%%'
            OR section_header ILIKE '%%heritage%%'
            OR provision_text ILIKE '%%heritage%%'
        )
    """, (f'%{council}%',))
    heritage_demo = cur.fetchone()[0]

    # Demolition provisions NOT in heritage context
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE document_id ILIKE %s
        AND provision_text ILIKE '%%demolition%%'
        AND NOT (
            v2_topic ILIKE '%%heritage%%'
            OR document_id ILIKE '%%heritage%%'
            OR section_header ILIKE '%%heritage%%'
            OR provision_text ILIKE '%%heritage%%'
        )
    """, (f'%{council}%',))
    general_demo = cur.fetchone()[0]

    print(f"  Heritage Demolition: {heritage_demo}")
    print(f"  General Demolition: {general_demo}")

    # Sample heritage demolition
    if heritage_demo > 0:
        cur.execute("""
            SELECT LEFT(provision_text, 150)
            FROM regulatory_provisions
            WHERE document_id ILIKE %s
            AND provision_text ILIKE '%%demolition%%'
            AND provision_text ILIKE '%%heritage%%'
            LIMIT 2
        """, (f'%{council}%',))
        print(f"\n  Sample HERITAGE demolition:")
        for row in cur.fetchall():
            text = row[0].replace('\n', ' ') if row[0] else ''
            print(f"    \"{text}...\"")

    # Sample general demolition
    if general_demo > 0:
        cur.execute("""
            SELECT LEFT(provision_text, 150)
            FROM regulatory_provisions
            WHERE document_id ILIKE %s
            AND provision_text ILIKE '%%demolition%%'
            AND NOT provision_text ILIKE '%%heritage%%'
            AND NOT v2_topic ILIKE '%%heritage%%'
            LIMIT 2
        """, (f'%{council}%',))
        print(f"\n  Sample GENERAL demolition:")
        for row in cur.fetchall():
            text = row[0].replace('\n', ' ') if row[0] else ''
            print(f"    \"{text}...\"")

# Check if v2_topic distinguishes them
print("\n" + "=" * 70)
print("v2_topic FOR DEMOLITION PROVISIONS")
print("=" * 70)

cur.execute("""
    SELECT v2_topic, COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%%Marrickville%%'
    AND provision_text ILIKE '%%demolition%%'
    GROUP BY v2_topic
    ORDER BY 2 DESC
""")
print("\nMarrickville demolition by v2_topic:")
for row in cur.fetchall():
    print(f"  {row[0] or 'NULL'}: {row[1]}")

cur.execute("""
    SELECT v2_topic, COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%%Leichhardt%%'
    AND provision_text ILIKE '%%demolition%%'
    GROUP BY v2_topic
    ORDER BY 2 DESC
""")
print("\nLeichhardt demolition by v2_topic:")
for row in cur.fetchall():
    print(f"  {row[0] or 'NULL'}: {row[1]}")

conn.close()
