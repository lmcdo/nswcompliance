"""
Create SQL dump using Python (no pg_dump required)
"""
from db_safety_wrapper import get_safe_connection
from datetime import datetime
from pathlib import Path

backup_dir = Path("backups")
backup_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
dump_file = backup_dir / f"nsw_planning_dump_{timestamp}.sql"

print(f"\n{'='*80}")
print(f"Creating SQL Dump: {dump_file}")
print(f"{'='*80}\n")

conn = get_safe_connection()
cur = conn.cursor()

with open(dump_file, 'w', encoding='utf-8') as f:
    # Write header
    f.write("-- PostgreSQL Database Dump\n")
    f.write(f"-- Generated: {datetime.now().isoformat()}\n")
    f.write("-- Database: nsw_planning\n\n")
    f.write("SET client_encoding = 'UTF8';\n")
    f.write("SET standard_conforming_strings = on;\n\n")

    # Get all tables
    cur.execute("""
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
    """)
    tables = [row[0] for row in cur.fetchall()]

    print(f"Found {len(tables)} tables to dump\n")

    for table in tables:
        print(f"Dumping table: {table}...", end=" ")

        # Get table schema
        cur.execute(f"""
            SELECT column_name, data_type, character_maximum_length, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table}'
            ORDER BY ordinal_position
        """)
        columns = cur.fetchall()

        # Write CREATE TABLE statement (simplified)
        f.write(f"\n-- Table: {table}\n")
        f.write(f"DROP TABLE IF EXISTS {table} CASCADE;\n")
        f.write(f"CREATE TABLE {table} (\n")

        col_defs = []
        for col in columns:
            col_name, data_type, max_len, nullable = col
            col_def = f"    {col_name} {data_type}"
            if max_len:
                col_def += f"({max_len})"
            if nullable == 'NO':
                col_def += " NOT NULL"
            col_defs.append(col_def)

        f.write(",\n".join(col_defs))
        f.write("\n);\n\n")

        # Get row count
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]

        if count > 0:
            # Write INSERT statements in batches
            cur.execute(f"SELECT * FROM {table}")
            rows = cur.fetchall()

            # Get column names
            col_names = [desc[0] for desc in cur.description]

            f.write(f"-- Data for {table} ({count:,} rows)\n")

            for row in rows:
                # Escape values
                values = []
                for val in row:
                    if val is None:
                        values.append("NULL")
                    elif isinstance(val, str):
                        # Escape single quotes
                        escaped = val.replace("'", "''").replace("\n", "\\n").replace("\r", "\\r")
                        values.append(f"'{escaped}'")
                    elif isinstance(val, (int, float)):
                        values.append(str(val))
                    else:
                        values.append(f"'{str(val)}'")

                f.write(f"INSERT INTO {table} ({', '.join(col_names)}) VALUES ({', '.join(values)});\n")

            f.write("\n")

        print(f"{count:,} rows")

    # Write indexes and constraints
    f.write("\n-- Indexes\n")
    cur.execute("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        AND indexname NOT LIKE '%pkey'
    """)
    for idx_name, idx_def in cur.fetchall():
        f.write(f"{idx_def};\n")

conn.close()

file_size = dump_file.stat().st_size
print(f"\n{'='*80}")
print(f"SQL Dump Complete!")
print(f"{'='*80}")
print(f"File: {dump_file}")
print(f"Size: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
print(f"{'='*80}\n")
