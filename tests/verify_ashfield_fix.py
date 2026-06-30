"""Verify Ashfield zone filter fix"""
import psycopg2
import os

# Test both LOCAL and SUPABASE
LOCAL_URL = 'postgresql://postgres@127.0.0.1:5432/nsw_planning'

print("=" * 60)
print("ASHFIELD FIX VERIFICATION")
print("=" * 60)

conn = psycopg2.connect(LOCAL_URL)
cur = conn.cursor()

# First check column names
cur.execute("""SELECT column_name FROM information_schema.columns WHERE table_name = 'dcp_general_requirements' ORDER BY ordinal_position""")
cols = [r[0] for r in cur.fetchall()]
print(f"Table columns: {cols[:10]}...")

# Table uses lga='Inner West' + former_council='Ashfield' (see route.ts lines 930, 932, 965, 968)

# Test Ashfield dwelling_house R2 query (the fixed one - line 966 in route.ts)
cur.execute('''
    SELECT COUNT(*) FROM dcp_general_requirements dgr
    WHERE dgr.lga = 'Inner West'
    AND dgr.former_council = 'Ashfield'
    AND 'dwelling_house' = ANY(dgr.development_types)
    AND (dgr.applicable_zones && ARRAY['R2']::text[] OR array_length(dgr.applicable_zones, 1) IS NULL)
''')
fixed_count = cur.fetchone()[0]

# Compare with OLD query (strict AND only - before fix)
cur.execute('''
    SELECT COUNT(*) FROM dcp_general_requirements dgr
    WHERE dgr.lga = 'Inner West'
    AND dgr.former_council = 'Ashfield'
    AND 'dwelling_house' = ANY(dgr.development_types)
    AND dgr.applicable_zones && ARRAY['R2']::text[]
''')
old_count = cur.fetchone()[0]

print(f'\nAshfield dwelling_house R2:')
print(f'  OLD query (strict): {old_count}')
print(f'  NEW query (fixed):  {fixed_count}')
print(f'  Improvement: +{fixed_count - old_count} requirements')

# Also test Supabase
print("\n" + "-" * 60)
print("SUPABASE CHECK")
print("-" * 60)

try:
    from dotenv import load_dotenv
    load_dotenv()
    SUPA_URL = os.getenv('SUPABASE_DB_URL')
    if SUPA_URL:
        supa_conn = psycopg2.connect(SUPA_URL)
        supa_cur = supa_conn.cursor()

        supa_cur.execute('''
            SELECT COUNT(*) FROM dcp_general_requirements dgr
            WHERE dgr.lga = 'Inner West'
            AND dgr.former_council = 'Ashfield'
            AND 'dwelling_house' = ANY(dgr.development_types)
            AND (dgr.applicable_zones && ARRAY['R2']::text[] OR array_length(dgr.applicable_zones, 1) IS NULL)
        ''')
        supa_fixed = supa_cur.fetchone()[0]

        supa_cur.execute('''
            SELECT COUNT(*) FROM dcp_general_requirements dgr
            WHERE dgr.lga = 'Inner West'
            AND dgr.former_council = 'Ashfield'
            AND 'dwelling_house' = ANY(dgr.development_types)
            AND dgr.applicable_zones && ARRAY['R2']::text[]
        ''')
        supa_old = supa_cur.fetchone()[0]

        print(f'Supabase Ashfield dwelling_house R2:')
        print(f'  OLD query (strict): {supa_old}')
        print(f'  NEW query (fixed):  {supa_fixed}')
        print(f'  Improvement: +{supa_fixed - supa_old} requirements')

        if supa_fixed == fixed_count:
            print(f'\n[OK] LOCAL and SUPABASE match: {fixed_count} requirements')
        else:
            print(f'\n[WARN] LOCAL ({fixed_count}) vs SUPABASE ({supa_fixed}) differ')

        supa_conn.close()
    else:
        print("SUPABASE_DB_URL not found in .env")
except Exception as e:
    print(f"Error connecting to Supabase: {e}")

conn.close()
print("\n" + "=" * 60)
