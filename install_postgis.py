import psycopg2

conn = psycopg2.connect(
    dbname='nsw_planning',
    user='postgres',
    password='Duffysql1!',
    host='localhost',
    port='5432'
)
cur = conn.cursor()

print('=== PostGIS Installation Check ===\n')

# Check if PostGIS is already installed
cur.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'postgis')")
has_postgis = cur.fetchone()[0]
print(f'PostGIS installed: {has_postgis}')

if not has_postgis:
    print('\nAttempting to install PostGIS extension...')
    try:
        cur.execute('CREATE EXTENSION IF NOT EXISTS postgis')
        cur.execute('CREATE EXTENSION IF NOT EXISTS postgis_topology')
        conn.commit()
        print('SUCCESS: PostGIS extension installed')
    except Exception as e:
        print(f'ERROR: Failed to install PostGIS: {e}')
        print('\nYou may need to:')
        print('1. Install PostGIS binaries for PostgreSQL 17')
        print('2. Download from: https://postgis.net/install/')
        print('3. Or use Stack Builder with PostgreSQL installation')
        conn.rollback()
else:
    # Check version
    try:
        cur.execute('SELECT PostGIS_Version()')
        version = cur.fetchone()[0]
        print(f'PostGIS version: {version}')
    except Exception as e:
        print(f'Error checking version: {e}')

cur.close()
conn.close()
