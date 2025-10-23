"""Show sample extracted requirements"""
from db_safety_wrapper import get_safe_connection
import os
from dotenv import load_dotenv

load_dotenv()

conn = get_safe_connection(
    host=os.getenv('PGHOST'),
    database=os.getenv('PGDATABASE'),
    user=os.getenv('PGUSER'),
    port=int(os.getenv('PGPORT', 5432))
)
conn.connect()
cur = conn.cursor()

print("=" * 80)
print("SAMPLE EXTRACTED REQUIREMENTS (First 10)")
print("=" * 80)

cur.execute("""
    SELECT
        precinct_name,
        category,
        requirement_text,
        value_numeric,
        unit,
        confidence
    FROM dcp_precinct_requirements
    ORDER BY id
    LIMIT 10
""")

for row in cur.fetchall():
    precinct, category, text, value, unit, conf = row
    print(f"\nPrecinct: {precinct}")
    print(f"  Category: {category}")
    print(f"  Text: {text}")
    if value:
        print(f"  Value: {value} {unit if unit else ''}")
    print(f"  Confidence: {conf}")

# Get summary statistics
cur.execute("""
    SELECT
        category,
        COUNT(*) as count,
        AVG(CASE WHEN confidence = 'high' THEN 1.0 ELSE 0.0 END) * 100 as high_conf_pct
    FROM dcp_precinct_requirements
    GROUP BY category
    ORDER BY count DESC
""")

print("\n" + "=" * 80)
print("CATEGORY BREAKDOWN")
print("=" * 80)
for category, count, high_conf_pct in cur.fetchall():
    print(f"{category:25s}: {count:3d} requirements ({high_conf_pct:.0f}% high confidence)")

print("\n" + "=" * 80)

conn.close()
